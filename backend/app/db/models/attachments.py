from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class Attachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evidência ancorada por escopo (DR-0017, fase EXPAND).

    Âncora polimórfica: ``scope`` + ``company_id`` + (``submission_id``, ``form_field_id``,
    ``asset_id``). 1:N por item inspecionado (INV-E1/Q7.3): a âncora é deliberadamente
    **não-única**. ``submission_value_id`` permanece temporariamente (deprecado) até a fase
    CONTRACT remover, junto com a reescrita do service/repository (etapa 3-4).
    """

    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_submission_value_id", "submission_value_id"),
        Index("ix_attachments_uploaded_by", "uploaded_by"),
        # Índices NÃO-ÚNICOS da âncora (INV-E1) — nenhum UNIQUE pode tocar a âncora.
        Index("ix_attachments_submission_id", "submission_id"),
        Index("ix_attachments_asset_id", "asset_id"),
        Index("ix_attachments_company_id", "company_id"),
        Index(
            "ix_attachments_submission_field_asset",
            "submission_id",
            "form_field_id",
            "asset_id",
        ),
    )

    # ── Âncora polimórfica (DR-0017) ─────────────────────────────────────────────
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    # 'component' | 'field' | 'submission' | 'asset' (CHECK entra na fase CONTRACT).
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True
    )
    form_field_id: Mapped[str | None] = mapped_column(ForeignKey("form_fields.id"), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    # Rótulo congelado do componente (evento); NULL para campo geral / asset-doc.
    component_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Vínculo legado (deprecado; removido na fase CONTRACT) ─────────────────────
    submission_value_id: Mapped[str | None] = mapped_column(
        ForeignKey("submission_values.id", ondelete="CASCADE"),
        nullable=True,
    )

    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships diretas da âncora (forward; back_populates entra na fase CONTRACT).
    company = relationship("Company")
    submission = relationship("Submission")
    form_field = relationship("FormField")
    asset = relationship("Asset")
    submission_value = relationship("SubmissionValue", back_populates="attachments")
    uploader = relationship("User", back_populates="attachments_uploaded")