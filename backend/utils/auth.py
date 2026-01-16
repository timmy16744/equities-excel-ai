"""Authentication service for JWT and password handling."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.database import User, RefreshToken, AuditLog

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings from environment
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION-" + secrets.token_hex(16))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Password operations
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # Token operations
    @staticmethod
    def create_access_token(
        user_id: int,
        email: str,
        is_admin: bool = False,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "is_admin": is_admin,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token_string() -> str:
        """Generate a secure refresh token string."""
        return secrets.token_urlsafe(32)

    async def create_refresh_token(self, user_id: int) -> Tuple[str, datetime]:
        """Create and store a refresh token for a user."""
        token_string = self.create_refresh_token_string()
        expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token = RefreshToken(
            user_id=user_id,
            token=token_string,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return token_string, expires_at

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None

    # User operations
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            logger.warning("Login attempt for non-existent user", email=email)
            return None
        if not user.is_active:
            logger.warning("Login attempt for inactive user", email=email)
            return None
        if not self.verify_password(password, user.hashed_password):
            logger.warning("Invalid password attempt", email=email)
            return None
        return user

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user."""
        hashed_password = self.hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_admin=is_admin,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("User created", email=email, is_admin=is_admin)
        return user

    async def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()

    async def change_password(self, user: User, new_password: str) -> None:
        """Change a user's password."""
        user.hashed_password = self.hash_password(new_password)
        await self.db.commit()
        logger.info("Password changed", user_id=user.id)

    # Refresh token operations
    async def get_refresh_token(self, token_string: str) -> Optional[RefreshToken]:
        """Get a refresh token by its string value."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token_string)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        """Revoke a refresh token."""
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )
        tokens = result.scalars().all()
        now = datetime.now(timezone.utc)
        for token in tokens:
            token.revoked = True
            token.revoked_at = now
        await self.db.commit()
        return len(tokens)

    async def refresh_access_token(self, refresh_token_string: str) -> Optional[Tuple[str, User]]:
        """Use a refresh token to get a new access token."""
        token = await self.get_refresh_token(refresh_token_string)
        if not token or not token.is_valid():
            return None

        user = await self.get_user_by_id(token.user_id)
        if not user or not user.is_active:
            return None

        access_token = self.create_access_token(
            user_id=user.id,
            email=user.email,
            is_admin=user.is_admin,
        )
        return access_token, user

    # Audit logging
    async def log_action(
        self,
        user_id: Optional[int],
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a security-relevant action."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        await self.db.commit()
        return audit_log


# Dependency functions for FastAPI
async def get_current_user(
    token: str,
    db: AsyncSession,
) -> Optional[User]:
    """Get the current user from a JWT token."""
    payload = AuthService.decode_access_token(token)
    if not payload:
        return None

    user_id = int(payload.get("sub", 0))
    if not user_id:
        return None

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    if not user or not user.is_active:
        return None

    return user
