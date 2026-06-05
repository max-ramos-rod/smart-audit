from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class SubmissionConformity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_conformities"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "form_field_id", name="uq_submission_conformities_submission_field"
        ),
        CheckConstraint(
            "status IN ('conforme', 'nao_conforme')", name="ck_submission_conformities_status"
        ),
        Index("ix_submission_conformities_submission_id", "submission_id"),
    )

    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    form_field_id: Mapped[str] = mapped_column(
        ForeignKey("form_fields.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission = relationship("Submission", back_populates="conformities")
    form_field = relationship("FormField", back_populates="conformities")
