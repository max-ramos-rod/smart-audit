from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        # M6: um componente (com pai) não pode ter client_id; o cliente é derivado da raiz.
        CheckConstraint(
            "parent_asset_id IS NULL OR client_id IS NULL",
            name="ck_assets_client_only_on_root",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'retired')",
            name="ck_assets_status",
        ),
        Index("ix_assets_company_parent", "company_id", "parent_asset_id"),
        Index("ix_assets_company_type", "company_id", "asset_type_id"),
        Index("ix_assets_company_client", "company_id", "client_id"),
    )

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    asset_type_id: Mapped[str] = mapped_column(ForeignKey("asset_types.id"), nullable=False)
    # NULL = raiz; preenchido = componente. Imutável após o create (SPEC r2, M5).
    parent_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=True
    )
    # NULL = patrimônio próprio; preenchido = ativo de cliente. Só permitido em raiz (M6).
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    identifier: Mapped[str] = mapped_column(String(180), nullable=False)
    attributes_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    asset_type = relationship("AssetType", back_populates="assets")
    client = relationship("Client")
    parent = relationship("Asset", remote_side="Asset.id", back_populates="components")
    components = relationship("Asset", back_populates="parent")
