from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class FormField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_fields"
    __table_args__ = (
        UniqueConstraint("form_version_id", "key", name="uq_form_fields_version_key"),
        UniqueConstraint("form_version_id", "position", name="uq_form_fields_version_position"),
        CheckConstraint(
            "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'section')",
            name="ck_form_fields_type",
        ),
        Index("ix_form_fields_form_version_id", "form_version_id"),
    )

    form_version_id: Mapped[str] = mapped_column(
        ForeignKey("form_versions.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Escopo de componente (DR-0002 Fases 2-4 / ADR-0016). NULL = campo geral; preenchido =
    # o campo repete por componente daquele tipo. Parte da versão publicada imutável (ADR-0005).
    component_type_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_types.id"), nullable=True
    )

    form_version = relationship("FormVersion", back_populates="fields")
    submission_values = relationship("SubmissionValue", back_populates="form_field")
    conformities = relationship("SubmissionConformity", back_populates="form_field")
