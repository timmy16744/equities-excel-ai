"""Authentication API endpoints."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.database import get_db, User
from backend.utils.auth import AuthService, get_current_user

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer(auto_error=False)

# Development mode bypass
DEV_MODE = os.getenv("ENVIRONMENT", "development") == "development"


# Request models
class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request body."""
    current_password: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""
    refresh_token: str


class CreateUserRequest(BaseModel):
    """Create user request body (admin only)."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False


# Response models
class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User info response."""
    id: int
    email: str
    full_name: Optional[str]
    is_admin: bool
    is_active: bool


# Fake user for development mode
class DevUser:
    """Fake user for development bypass."""
    id = 0
    email = "dev@localhost"
    full_name = "Development User"
    is_admin = True
    is_active = True
    hashed_password = ""


# Dependencies
async def get_current_active_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user."""
    # Development mode bypass - skip auth entirely
    if DEV_MODE:
        logger.debug("Dev mode: bypassing authentication")
        return DevUser()  # type: ignore

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_current_user(credentials.credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    """Dependency to require admin access."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Routes
@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and get access/refresh tokens."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        # Log failed attempt
        await auth_service.log_action(
            user_id=None,
            action="login_failed",
            resource="auth",
            details={"email": login_data.email},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens
    access_token = auth_service.create_access_token(
        user_id=user.id,
        email=user.email,
        is_admin=user.is_admin,
    )
    refresh_token, _ = await auth_service.create_refresh_token(user.id)

    # Update last login
    await auth_service.update_last_login(user)

    # Log successful login
    await auth_service.log_action(
        user_id=user.id,
        action="login",
        resource="auth",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    logger.info("User logged in", user_id=user.id, email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,  # 30 minutes in seconds
    )


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logout and revoke all refresh tokens."""
    auth_service = AuthService(db)

    revoked_count = await auth_service.revoke_all_user_tokens(user.id)

    await auth_service.log_action(
        user_id=user.id,
        action="logout",
        resource="auth",
        details={"revoked_tokens": revoked_count},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    logger.info("User logged out", user_id=user.id)

    return {"status": "logged_out", "revoked_tokens": revoked_count}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Get a new access token using a refresh token."""
    auth_service = AuthService(db)

    result = await auth_service.refresh_access_token(refresh_data.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, user = result

    # Create new refresh token and revoke the old one
    old_token = await auth_service.get_refresh_token(refresh_data.refresh_token)
    if old_token:
        await auth_service.revoke_refresh_token(old_token)

    new_refresh_token, _ = await auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's password."""
    auth_service = AuthService(db)

    # Verify current password
    if not auth_service.verify_password(password_data.current_password, user.hashed_password):
        await auth_service.log_action(
            user_id=user.id,
            action="password_change_failed",
            resource="auth",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Change password
    await auth_service.change_password(user, password_data.new_password)

    # Revoke all existing refresh tokens (force re-login)
    await auth_service.revoke_all_user_tokens(user.id)

    await auth_service.log_action(
        user_id=user.id,
        action="password_changed",
        resource="auth",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return {"status": "password_changed"}


# Admin-only routes
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user (admin only)."""
    auth_service = AuthService(db)

    # Check if user already exists
    existing = await auth_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Validate password
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user = await auth_service.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        is_admin=user_data.is_admin,
    )

    await auth_service.log_action(
        user_id=admin.id,
        action="create_user",
        resource="users",
        resource_id=str(user.id),
        details={"created_email": user.email, "is_admin": user.is_admin},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )
