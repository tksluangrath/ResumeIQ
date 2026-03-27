from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import User
from api.dependencies import get_db, require_current_user
from api.models import TokenResponse, UserLoginRequest, UserPublic, UserRegisterRequest
from api.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user: User | None = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
async def me(
    current_user: User = Depends(require_current_user),
) -> UserPublic:
    return UserPublic(
        id=current_user.id,
        email=current_user.email,
        plan=current_user.plan,
        scan_count=current_user.scan_count,
        created_at=current_user.created_at,
    )
