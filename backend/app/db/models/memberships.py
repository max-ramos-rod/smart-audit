from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_memberships_company_user"),
        CheckConstraint(
            "role IN ('OWNER', 'ADMIN', 'MANAGER', 'INSPECTOR', 'VIEWER')",
            name="ck_memberships_role",
        ),
        Index("ix_memberships_company_id", "company_id"),
        Index("ix_memberships_user_id", "user_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    company = relationship("Company", back_populates="memberships")
    user = relationship("User", back_populates="memberships")