from __future__ import annotations

import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from api.constants import MAX_PDF_BYTES, MAX_JD_CHARS, MIN_JD_CHARS
from api.db import Scan
from api.dependencies import check_and_increment_scan, get_current_user, get_db, get_extractor, get_matcher, get_scorer
from api.models import MatchResponse
from engine.extractor import EntityExtractor
from engine.matcher import SemanticMatcher
from engine.parser import extract_text_from_pdf
from engine.scorer import MatchScorer
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["matching"])


@router.post("/match", response_model=MatchResponse)
async def match_resume(
    resume: UploadFile,
    job_description: str = Form(...),
    extractor: EntityExtractor = Depends(get_extractor),
    matcher: SemanticMatcher = Depends(get_matcher),
    scorer: MatchScorer = Depends(get_scorer),
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    start_ms = time.monotonic()

    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="resume must be a PDF file.")

    pdf_bytes = await resume.read()

    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF file exceeds 5 MB limit.")
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=422, detail="PDF file is empty.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File does not appear to be a valid PDF.")

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

    # pdfplumber requires a real file path — UploadFile bytes must go through a temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            resume_text = extract_text_from_pdf(Path(tmp.name))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from the PDF.")

    resume_entities = extractor.extract(resume_text)
    jd_entities = extractor.extract(jd)
    semantic_sim = matcher.similarity(resume_text, jd)
    report = scorer.score(resume_entities, jd_entities, semantic_sim)

    if current_user is not None:
        await check_and_increment_scan(current_user, db)
        db.add(Scan(
            user_id=current_user.id,
            endpoint="match",
            overall_score=report.overall_score,
            job_snippet=jd[:200],
        ))
        await db.commit()

    return MatchResponse(
        overall_score=report.overall_score,
        breakdown=report.breakdown,
        recommendations=report.recommendations,
        processing_time_ms=int((time.monotonic() - start_ms) * 1000),
    )
