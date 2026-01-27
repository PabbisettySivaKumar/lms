"""
Holiday SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, Index  # type: ignore
from backend.db import Base


class Holiday(Base):
    """Holidays table"""
    __tablename__ = "holidays"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, unique=True)
    year = Column(Integer, nullable=False)
    is_optional = Column(Boolean, default=False, comment="Optional holiday")
    
    __table_args__ = (
        Index("idx_year", "year"),
        Index("idx_date", "date"),
        Index("idx_year_optional", "year", "is_optional"),
    )
