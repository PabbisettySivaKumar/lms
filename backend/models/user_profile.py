"""
User profile table - 1:1 with users (profile, address, family, emergency contact).
"""
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Index, text  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from datetime import datetime, date
from backend.db import Base


class UserProfile(Base):
    """User profiles table - one row per user (1:1)."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        comment="1:1 with users",
    )
    profile_picture_url = Column(String(500), nullable=True)
    dob = Column(Date, nullable=True)
    blood_group = Column(String(10), nullable=True)
    address = Column(Text, nullable=True, comment="Current address")
    permanent_address = Column(Text, nullable=True, comment="Permanent address")
    father_name = Column(String(255), nullable=True)
    father_dob = Column(Date, nullable=True)
    mother_name = Column(String(255), nullable=True)
    mother_dob = Column(Date, nullable=True)
    spouse_name = Column(String(255), nullable=True)
    spouse_dob = Column(Date, nullable=True)
    children_names = Column(Text, nullable=True, comment="Comma-separated or JSON array")
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="profile", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_user_profile_user_id", "user_id"),
    )
