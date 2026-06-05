from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="starter", server_default="starter"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    cnpj: Mapped[str | None] = mapped_column(String(18), nullable=True)
    timezone: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="America/Sao_Paulo", server_default="America/Sao_Paulo"
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    memberships = relationship("Membership", back_populates="company")
    forms = relationship("Form", back_populates="company")
    submissions = relationship("Submission", back_populates="company")
    teams = relationship("Team", back_populates="company")
