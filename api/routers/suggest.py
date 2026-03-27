from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from api.constants import MAX_JD_CHARS, MAX_PDF_BYTES, MIN_JD_CHARS
from api.db import Scan
from api.dependencies import check_and_increment_scan, get_current_user, get_db, get_extractor, get_llm, get_matcher, get_scorer
from api.models import BulletRewriteResponse, SuggestResponse
from engine.extractor import EntityExtractor
from engine.llm.base import BaseLLM, LLMConnectionError, LLMResponseError
from engine.matcher import SemanticMatcher
from engine.parser import extract_text_from_pdf
from engine.profile import UserProfile
from engine.scorer import MatchScorer
from engine.suggester import suggest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["suggest"])


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_resume(
    resume_pdf: UploadFile,
    job_description: str = Form(...),
    profile_json: str | None = Form(default=None),
    extractor: EntityExtractor = Depends(get_extractor),
    matcher: SemanticMatcher = Depends(get_matcher),
    scorer: MatchScorer = Depends(get_scorer),
    llm: BaseLLM = Depends(get_llm),
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestResponse:
    start_ms = time.monotonic()

    # --- Validate PDF ---
    if resume_pdf.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="resume_pdf must be a PDF file.")
    pdf_bytes = await resume_pdf.read()
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="resume_pdf exceeds 5 MB limit.")
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=422, detail="resume_pdf is empty.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File does not appear to be a valid PDF.")

    # --- Validate job description ---
    jd = job_description.strip()
    if len(jd) < MIN_JD_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"job_description must be at least {MIN_JD_CHARS} characters.",
        )
    if len(jd) > MAX_JD_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"job_description must not exceed {MAX_JD_CHARS} characters.",
        )

    # --- Optional profile ---
    profile: UserProfile | None = None
    if profile_json is not None:
        try:
            profile = UserProfile.model_validate(json.loads(profile_json))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"profile_json is invalid: {exc}")

    # --- PDF → text via temp file ---
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as pdf_tmp:
        pdf_tmp.write(pdf_bytes)
        pdf_tmp.flush()
        try:
            resume_text = extract_text_from_pdf(Path(pdf_tmp.name))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from resume_pdf.")

    # --- Engine pipeline ---
    resume_entities = extractor.extract(resume_text)
    jd_entities = extractor.extract(jd)
    semantic_sim = matcher.similarity(resume_text, jd)
    report = scorer.score(resume_entities, jd_entities, semantic_sim)

    try:
        result = suggest(
            resume_text=resume_text,
            job_description=jd,
            report=report,
            llm=llm,
            profile=profile,
        )
    except LLMConnectionError as exc:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {exc}")
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=f"LLM returned an invalid response: {exc}")

    bullet_rewrites = [
        BulletRewriteResponse(
            original=br.original,
            rewritten=br.rewritten,
            section=br.section,
            context=br.context,
        )
        for br in result.bullet_rewrites
    ]

    if current_user is not None:
        await check_and_increment_scan(current_user, db)
        db.add(Scan(
            user_id=current_user.id,
            endpoint="suggest",
            overall_score=report.overall_score,
            job_snippet=jd[:200],
        ))
        await db.commit()

    return SuggestResponse(
        overall_score=report.overall_score,
        breakdown=report.breakdown,
        bullet_rewrites=bullet_rewrites,
        skill_gaps=result.skill_gaps,
        injected_keywords=result.injected_keywords,
        career_summary=result.career_summary,
        provider=result.provider,
        processing_time_ms=int((time.monotonic() - start_ms) * 1000),
    )
