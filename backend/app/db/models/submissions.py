from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    desc,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class Submission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'in_progress', 'completed', 'cancelled')",
            name="ck_submissions_status",
        ),
        Index("ix_submissions_company_id", "company_id"),
        Index("ix_submissions_form_version_id", "form_version_id"),
        Index("ix_submissions_created_by", "created_by"),
        Index("ix_submissions_status", "status"),
        Index(
            "ix_submissions_company_status_created_at", "company_id", "status", desc("created_at")
        ),
        Index("ix_submissions_company_asset", "company_id", "asset_id"),
    )

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    form_version_id: Mapped[str] = mapped_column(ForeignKey("form_versions.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Vínculo opcional inspeção→ativo (DR-0002 Fase 1). NULL = inspeção sem ativo
    # (comportamento atual). Sem CASCADE: ativos são soft-deletados, nunca removidos.
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default=text("'draft'")
    )
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answers_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    # Identidade congelada por componente (DR-0002 Fases 2-4 / ADR-0016, Q1.1):
    # { <asset_id>: { label, type, path } }. NULL = inspeção sem componentes (atual).
    # Gravado uma vez por componente em save_answers; preserva o laudo histórico
    # contra renomeação/desativação do ativo.
    components_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    company = relationship("Company", back_populates="submissions")
    creator = relationship("User", back_populates="submissions_created")
    asset = relationship("Asset")
    form_version = relationship("FormVersion", back_populates="submissions")
    values = relationship("SubmissionValue", back_populates="submission")
    conformities = relationship(
        "SubmissionConformity", back_populates="submission", cascade="all, delete-orphan"
    )