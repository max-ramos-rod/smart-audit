from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class FormVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("form_id", "version", name="uq_form_versions_form_version"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')", name="ck_form_versions_status"
        ),
        Index("ix_form_versions_form_id", "form_id"),
        Index("ix_form_versions_status", "status"),
    )

    form_id: Mapped[str] = mapped_column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    form = relationship("Form", back_populates="versions")
    creator = relationship("User", back_populates="form_versions_created")
    fields = relationship("FormField", back_populates="form_version")
    submissions = relationship("Submission", back_populates="form_version")