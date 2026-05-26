from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.models.users import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import AuthenticatedUserResponse, TokenResponse


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

    @staticmethod
    def serialize_user(user: User) -> AuthenticatedUserResponse:
        return AuthenticatedUserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
        )
