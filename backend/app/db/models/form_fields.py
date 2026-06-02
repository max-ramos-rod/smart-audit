from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


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

    form_version_id: Mapped[str] = mapped_column(ForeignKey("form_versions.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    form_version = relationship("FormVersion", back_populates="fields")
    submission_values = relationship("SubmissionValue", back_populates="form_field")
