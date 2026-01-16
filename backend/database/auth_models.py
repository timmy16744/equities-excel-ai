"""Authentication and authorization database models."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database.models import Base


# Association table for User-Role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User account for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Role(Base):
    """Role for role-based access control."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    permissions = Column(JSON, default=list)  # List of permission strings
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class AuditLog(Base):
    """Audit trail for security-relevant actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(50), nullable=False, index=True)  # login, logout, create, update, delete
    resource = Column(String(100), nullable=False)  # settings, user, etc.
    resource_id = Column(String(100))  # Optional ID of affected resource
    details = Column(JSON)  # Additional action details
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource} by user_id={self.user_id}>"


class RefreshToken(Base):
    """Refresh tokens for JWT authentication."""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    revoked_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        if self.revoked:
            return False
        return datetime.now(self.expires_at.tzinfo) < self.expires_at

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} revoked={self.revoked}>"


# Default roles to seed
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Full system access",
        "permissions": ["*"],
    },
    {
        "name": "user",
        "description": "Standard user access",
        "permissions": [
            "read:agents",
            "read:insights",
            "read:performance",
            "read:settings",
            "write:ui_preferences",
        ],
    },
    {
        "name": "readonly",
        "description": "Read-only access",
        "permissions": [
            "read:agents",
            "read:insights",
            "read:performance",
        ],
    },
]
