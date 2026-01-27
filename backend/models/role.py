"""
Role-related SQLAlchemy models
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, Index  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime
from backend.db import Base


class Role(Base):
    """Roles table"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="Role identifier")
    display_name = Column(String(100), nullable=False, comment="Human-readable role name")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    role_scopes = relationship("RoleScope", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_name", "name"),
        Index("idx_active", "is_active"),
    )


class RoleScope(Base):
    """Role scopes table - maps roles to OAuth2 scopes"""
    __tablename__ = "role_scopes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    scope_name = Column(String(100), nullable=False, comment="OAuth2 scope name")
    created_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    role = relationship("Role", back_populates="role_scopes")
    
    __table_args__ = (
        UniqueConstraint("role_id", "scope_name", name="unique_role_scope"),
        Index("idx_role_id", "role_id"),
        Index("idx_scope_name", "scope_name"),
    )


class UserRole(Base):
    """User roles table - many-to-many user-role relationship"""
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, comment="User who assigned this role")
    assigned_at = Column(DateTime, default=datetime.utcnow, server_default="CURRENT_TIMESTAMP")
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "is_active", name="unique_user_role_active"),
        Index("idx_user_id", "user_id"),
        Index("idx_role_id", "role_id"),
        Index("idx_active", "is_active"),
    )
