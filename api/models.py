from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from engine.scorer import ScoreBreakdown


class WeakBullet(BaseModel):
    model_config = ConfigDict(frozen=True)

    section: str
    # Mutually exclusive: experience entries carry `company`, project entries carry `project`.
    # Both are optional because the optimizer dict schema is not discriminated at the source.
    company: str | None = None
    project: str | None = None
    bullet: str
    hint: str | None = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_score: float
    breakdown: ScoreBreakdown
    recommendations: list[str]
    processing_time_ms: int


class ImproveResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_score: float
    breakdown: ScoreBreakdown
    recommendations: list[str]
    injected_skills: list[str]
    weak_bullets: list[WeakBullet]
    notes: list[str]
    # None when LaTeX generation is skipped or fails
    latex_source: str | None
    # Reserved for Phase 4 pre-signed PDF URL; always None in Phase 2
    pdf_url: str | None = None
    processing_time_ms: int


class BulletRewriteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: str
    rewritten: str
    section: str
    context: str


class SuggestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_score: float
    breakdown: ScoreBreakdown
    bullet_rewrites: list[BulletRewriteResponse]
    skill_gaps: list[str]
    injected_keywords: list[str]
    career_summary: str
    provider: str
    processing_time_ms: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    version: str
    env: str


# ── Phase 4: Auth ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    email: str
    plan: str
    scan_count: int
    created_at: datetime


# ── Phase 4: Billing ─────────────────────────────────────────────────────────

class CheckoutResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkout_url: str


class PortalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    portal_url: str


class BillingStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: str
    scan_count: int
    scan_limit: int | None  # None = unlimited
    stripe_customer_id: str | None


# ── Phase 4: Scan History ────────────────────────────────────────────────────

class ScanRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    endpoint: str
    overall_score: float
    job_snippet: str
    created_at: datetime


class PaginatedScans(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ScanRecord]
    total: int
    page: int
    page_size: int
    has_next: bool
