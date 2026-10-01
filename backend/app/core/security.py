from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Optional, Union
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.entities import User, UserRole

# CryptContext configured with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


# ==============================================================================
# Password Hashing & Verification (supports bcrypt 4.x/5.x & passlib)
# ==============================================================================

def get_password_hash(password: str) -> str:
    """Hashes plaintext password using bcrypt (max 72 bytes per standard)"""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plaintext password against stored bcrypt hash"""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False


# ==============================================================================
# JWT Generation & Decoding
# ==============================================================================

def create_access_token(
    subject: Union[str, Any],
    extra_claims: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates signed JWT access token with expiration timestamp"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Decodes and validates JWT signature and expiration"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ==============================================================================
# Current User Dependency
# ==============================================================================

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates JWT token from request header
    and retrieves the corresponding User from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = verify_token(token)
    if not payload:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with token does not exist",
        )

    return user


# ==============================================================================
# Role-Based Access Control (RBAC) Dependency Injection
# ==============================================================================

def require_role(allowed_roles: Union[str, UserRole, List[Union[str, UserRole]]]) -> Callable:
    """
    Dependency factory for Role-Based Access Control (RBAC).

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_role("admin"))])
        @router.get("/review-queue", dependencies=[Depends(require_role("hse_officer"))])
        @router.get("/site-reports", dependencies=[Depends(require_role(["hse_officer", "site_manager"]))])

    Roles:
        - 'hse_officer': Full safety dashboard & review queue access
        - 'site_manager': Their site's reports and logs
        - 'admin': User management & full platform administration
    """
    if isinstance(allowed_roles, (str, UserRole)):
        roles_list = [str(allowed_roles)]
    else:
        roles_list = [str(r) for r in allowed_roles]

    # Convert UserRole enum or str to string value
    normalized_roles = []
    for r in roles_list:
        normalized_roles.append(r.value if isinstance(r, UserRole) else str(r))

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_val = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)

        # Admin has superuser override on all routes
        if user_role_val == UserRole.admin.value or user_role_val == "admin":
            return current_user

        if user_role_val not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires role '{', '.join(normalized_roles)}'. Current role: '{user_role_val}'",
            )
        return current_user

    return role_checker
