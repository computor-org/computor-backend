"""Durable public grading admissions, independent of mutable Result rows."""

from sqlalchemy import Column, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class PublicGradingReservation(Base):
    __tablename__ = "public_grading_reservation"
    __table_args__ = (
        Index("public_grading_reservation_open_idx", "created_at",
              postgresql_where=text("released_at IS NULL")),
    )

    workflow_id = Column(String(255), primary_key=True)
    # Deliberately no FK: deleting an artifact or Result must not free a live job.
    result_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    released_at = Column(DateTime(timezone=True))
