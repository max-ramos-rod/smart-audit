from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Form(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forms"
    __table_args__ = (
        Index("ix_forms_company_id", "company_id"),
        Index("ix_forms_company_active", "company_id", "is_active"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    company = relationship("Company", back_populates="forms")
    creator = relationship("User", back_populates="forms_created")
    versions = relationship("FormVersion", back_populates="form")
