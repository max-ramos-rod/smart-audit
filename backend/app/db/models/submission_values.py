from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class SubmissionValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_values"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "form_field_id",
            "asset_id",
            name="uq_submission_values_submission_field_asset",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_submission_values_submission_id", "submission_id"),
        Index("ix_submission_values_form_field_id", "form_field_id"),
        Index("ix_submission_values_asset", "asset_id"),
    )

    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    form_field_id: Mapped[str] = mapped_column(ForeignKey("form_fields.id"), nullable=False)
    # Dimensão de componente (DR-0002 Fases 2-4 / ADR-0016). NULL = campo geral
    # (comportamento atual). Sem CASCADE: ativos são soft-deletados, nunca removidos.
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    submission = relationship("Submission", back_populates="values")
    form_field = relationship("FormField", back_populates="submission_values")