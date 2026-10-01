from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    require_role,
    verify_password,
)
from app.models.entities import Site, User, UserRole
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter()


# ==============================================================================
# Authentication Endpoints
# ==============================================================================

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new HSE officer, Site Manager, or Administrator.
    Returns the user profile along with a signed JWT access token.
    """
    # 1. Check if email is already taken
    stmt = select(User).where(User.email == payload.email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # 2. Check if site_id is valid if provided
    if payload.site_id:
        site_stmt = select(Site).where(Site.id == payload.site_id)
        site = (await db.execute(site_stmt)).scalar_one_or_none()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Site with ID {payload.site_id} does not exist",
            )

    # 3. Create user with hashed password
    hashed_pw = get_password_hash(payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hashed_pw,
        role=payload.role or UserRole.hse_officer,
        site_id=payload.site_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 4. Generate JWT access token
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.JWT_EXPIRY,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates user credentials and returns a JWT access token.
    """
    # 1. Look up user by email
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Generate JWT access token
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.JWT_EXPIRY,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current Authenticated User",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the profile and role details of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)


# ==============================================================================
# Role-Protected Verification Endpoints
# ==============================================================================

@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    summary="List All Users (Admin Only)",
    dependencies=[Depends(require_role("admin"))],
)
async def list_all_users(db: AsyncSession = Depends(get_db)):
    """
    Protected route accessible exclusively to Administrator accounts.
    """
    stmt = select(User).order_by(User.id)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/review-queue/verify-access",
    summary="Verify HSE Officer Access",
)
async def verify_hse_access(
    current_user: User = Depends(require_role("hse_officer")),
):
    """
    Protected route verifying full review queue and precursor triage access.
    """
    return {
        "access": "granted",
        "user_id": current_user.id,
        "name": current_user.name,
        "role": current_user.role,
        "message": "Authorized for full safety dashboard & HITL review queue operations",
    }
