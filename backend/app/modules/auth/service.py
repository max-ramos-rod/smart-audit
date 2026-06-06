import logging
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.text import MIMEText

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.password_reset_tokens import PasswordResetToken
from app.db.models.users import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import AuthenticatedUserResponse, TokenResponse

logger = logging.getLogger(__name__)

_RESET_TOKEN_TTL_HOURS = 1


class AuthService:
    def __init__(self, repository: AuthRepository | None = None) -> None:
        self.repository = repository or AuthRepository()

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        user = await self.repository.get_user_by_email(db, email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha invalidos.",
            )

        token, expires_in = create_access_token(str(user.id))
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=self.serialize_user(user),
        )

    async def get_current_user(self, db: AsyncSession, user_id: str) -> User:
        user = await self.repository.get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario autenticado invalido.",
            )
        return user

    async def request_password_reset(self, db: AsyncSession, email: str) -> None:
        user = await self.repository.get_user_by_email(db, email)
        if user is None or not user.is_active:
            return  # don't reveal whether email exists

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=_RESET_TOKEN_TTL_HOURS)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        await self.repository.create_reset_token(db, reset_token)
        await db.commit()

        settings = get_settings()
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        self._deliver_reset_link(email, reset_url, settings)

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None:
        now = datetime.now(UTC)
        reset_token = await self.repository.get_valid_reset_token(db, token, now)
        if reset_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalido ou expirado.",
            )

        reset_token.user.password_hash = hash_password(new_password)
        reset_token.used_at = now
        db.add(reset_token.user)
        db.add(reset_token)
        await db.commit()

    @staticmethod
    def _deliver_reset_link(email: str, reset_url: str, settings) -> None:
        if settings.smtp_host:
            try:
                msg = MIMEText(
                    f"Clique no link abaixo para redefinir sua senha (válido por "
                    f"{_RESET_TOKEN_TTL_HOURS}h):\n\n{reset_url}"
                )
                msg["Subject"] = "Smart Audit — redefinição de senha"
                msg["From"] = settings.smtp_from
                msg["To"] = email
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                    if settings.smtp_user and settings.smtp_password:
                        smtp.starttls()
                        smtp.login(settings.smtp_user, settings.smtp_password)
                    smtp.send_message(msg)
            except Exception:
                logger.exception("Falha ao enviar e-mail de recuperacao para %s", email)
        else:
            logger.info(
                "PASSWORD RESET | email=%s | url=%s", email, reset_url
            )

    @staticmethod
    def serialize_user(user: User) -> AuthenticatedUserResponse:
        return AuthenticatedUserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
        )
