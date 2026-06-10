from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class AssetType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_types"
    __table_args__ = (
        Index("ix_asset_types_company_id", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Opcional (Q5): quando presente, descreve os atributos esperados. A validação de
    # attributes_json contra este schema NÃO faz parte da Fase 1 (ver SPEC r2, M1).
    attributes_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    company = relationship("Company")
    assets = relationship("Asset", back_populates="asset_type")
