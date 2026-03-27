from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from api.constants import MAX_JD_CHARS, MAX_PDF_BYTES, MAX_TEX_BYTES, MIN_JD_CHARS
from api.db import Scan
from api.dependencies import check_and_increment_scan, get_current_user, get_db, get_extractor, get_matcher, get_scorer
from api.models import ImproveResponse, WeakBullet
from engine.extractor import EntityExtractor
from engine.latex_builder import parse_tex_to_resume_data, render_latex
from engine.matcher import SemanticMatcher
from engine.optimizer import optimize
from engine.parser import extract_text_from_pdf
from engine.profile import UserProfile
from engine.scorer import MatchScorer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["improve"])


@router.post("/improve", response_model=ImproveResponse)
async def improve_resume(
    resume_pdf: UploadFile,
    resume_tex: UploadFile,
    job_description: str = Form(...),
    profile_json: str | None = Form(default=None),
    extractor: EntityExtractor = Depends(get_extractor),
    matcher: SemanticMatcher = Depends(get_matcher),
    scorer: MatchScorer = Depends(get_scorer),
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImproveResponse:
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

    # --- Validate .tex ---
    tex_bytes = await resume_tex.read()
    if len(tex_bytes) > MAX_TEX_BYTES:
        raise HTTPException(status_code=413, detail="resume_tex exceeds 1 MB limit.")
    if len(tex_bytes) == 0:
        raise HTTPException(status_code=422, detail="resume_tex is empty.")
    if resume_tex.filename and not resume_tex.filename.endswith(".tex"):
        raise HTTPException(status_code=422, detail="resume_tex must be a .tex file.")

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

    # --- .tex → ResumeData via temp file ---
    with tempfile.NamedTemporaryFile(suffix=".tex", delete=True) as tex_tmp:
        tex_tmp.write(tex_bytes)
        tex_tmp.flush()
        try:
            resume_data = parse_tex_to_resume_data(Path(tex_tmp.name))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to parse .tex file: {exc}")

    # --- Engine pipeline ---
    resume_entities = extractor.extract(resume_text)
    jd_entities = extractor.extract(jd)
    semantic_sim = matcher.similarity(resume_text, jd)
    report = scorer.score(resume_entities, jd_entities, semantic_sim)
    opt_result = optimize(report, resume_data, profile=profile)

    # render_latex failure is non-fatal — latex_source: str | None is the documented contract
    latex_source: str | None = None
    try:
        latex_source = render_latex(opt_result.resume)
    except Exception:
        logger.exception("LaTeX rendering failed; returning latex_source=None")

    if current_user is not None:
        await check_and_increment_scan(current_user, db)
        db.add(Scan(
            user_id=current_user.id,
            endpoint="improve",
            overall_score=report.overall_score,
            job_snippet=jd[:200],
        ))
        await db.commit()

    # model_validate handles varying dict keys (company vs project vs hint) cleanly
    weak_bullets = [WeakBullet.model_validate(wb) for wb in opt_result.weak_bullets]

    return ImproveResponse(
        overall_score=report.overall_score,
        breakdown=report.breakdown,
        recommendations=report.recommendations,
        injected_skills=opt_result.injected_skills,
        weak_bullets=weak_bullets,
        notes=opt_result.notes,
        latex_source=latex_source,
        pdf_url=None,
        processing_time_ms=int((time.monotonic() - start_ms) * 1000),
    )
