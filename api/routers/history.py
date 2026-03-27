from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import Scan, User
from api.dependencies import get_db, require_current_user
from api.models import PaginatedScans, ScanRecord

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=PaginatedScans)
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedScans:
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).select_from(Scan).where(Scan.user_id == current_user.id)
    )
    total: int = count_result.scalar_one()

    rows_result = await db.execute(
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    scans = rows_result.scalars().all()

    return PaginatedScans(
        items=[
            ScanRecord(
                id=s.id,
                endpoint=s.endpoint,
                overall_score=s.overall_score,
                job_snippet=s.job_snippet,
                created_at=s.created_at,
            )
            for s in scans
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


@router.get("/{scan_id}", response_model=ScanRecord)
async def get_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanRecord:
    scan: Scan | None = await db.get(Scan, scan_id)
    if scan is None or scan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanRecord(
        id=scan.id,
        endpoint=scan.endpoint,
        overall_score=scan.overall_score,
        job_snippet=scan.job_snippet,
        created_at=scan.created_at,
    )
