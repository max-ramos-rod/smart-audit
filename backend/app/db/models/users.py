from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    memberships = relationship("Membership", back_populates="user")
    forms_created = relationship("Form", back_populates="creator")
    form_versions_created = relationship("FormVersion", back_populates="creator")
    submissions_created = relationship("Submission", back_populates="creator")
    attachments_uploaded = relationship("Attachment", back_populates="uploader")
