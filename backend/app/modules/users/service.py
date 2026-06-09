import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.email import EmailService
from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.core.security import hash_password
from app.db.models.memberships import Membership
from app.db.models.password_reset_tokens import PasswordResetToken
from app.db.models.users import User
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.auth.repository import AuthRepository
from app.modules.companies.repository import CompanyRepository
from app.modules.memberships.repository import MembershipRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreateRequest,
    UserInviteRequest,
    UserListItemResponse,
    UserResponse,
    UserRevokedItemResponse,
    UserUpdateRequest,
)

ALLOWED_ROLES = {"OWNER", "ADMIN", "MANAGER", "INSPECTOR", "VIEWER"}


class UserService:
    def __init__(
        self,
        repository: UserRepository | None = None,
        membership_repository: MembershipRepository | None = None,
        audit_repository: AuditLogRepository | None = None,
        auth_repository: AuthRepository | None = None,
        company_repository: CompanyRepository | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.repository = repository or UserRepository()
        self.membership_repository = membership_repository or MembershipRepository()
        self.audit_repository = audit_repository or AuditLogRepository()
        self.auth_repository = auth_repository or AuthRepository()
        self.company_repository = company_repository or CompanyRepository()
        self.email_service = email_service or EmailService()

    async def list_users(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[UserListItemResponse], PageMeta]:
        memberships, total = await self.repository.list_users_by_company(
            db, str(membership.company_id), params
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_user_list_item(item) for item in memberships], meta

    async def get_user(
        self, db: AsyncSession, membership: Membership, user_id: str
    ) -> UserResponse:
        target_membership = await self.repository.get_company_user(
            db, str(membership.company_id), user_id
        )
        if target_membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado."
            )
        return self.serialize_user(target_membership)

    async def create_user(
        self, db: AsyncSession, membership: Membership, payload: UserCreateRequest
    ) -> UserResponse:
        self.validate_role(payload.role)

        existing_user = await self.repository.get_user_by_email(db, payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ja existe usuario com esse email."
            )

        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            is_active=payload.is_active,
        )
        await self.repository.create_user(db, user)

        created_membership = Membership(
            company_id=membership.company_id,
            user_id=user.id,
            role=payload.role,
        )
        await self.repository.create_membership(db, created_membership)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="user.created",
            target_user_id=str(user.id),
            meta={"user_name": payload.name, "email": payload.email, "role": payload.role},
        )
        await db.commit()

        target_membership = await self.repository.get_company_user(
            db, str(membership.company_id), str(user.id)
        )
        assert target_membership is not None
        return self.serialize_user(target_membership)

    async def invite_user(
        self, db: AsyncSession, membership: Membership, payload: UserInviteRequest
    ) -> UserResponse:
        """Cria o usuario sem senha utilizavel e envia um link de convite.

        O usuario define a propria senha pelo link (mesma tela/endpoint do reset
        de senha). Reaproveita a tabela password_reset_tokens com um TTL maior.
        """
        self.validate_role(payload.role)

        existing_user = await self.repository.get_user_by_email(db, payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ja existe usuario com esse email."
            )

        # Senha aleatoria inutilizavel: o convidado nao consegue logar ate
        # definir a propria senha pelo link de convite.
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            is_active=True,
        )
        await self.repository.create_user(db, user)

        created_membership = Membership(
            company_id=membership.company_id,
            user_id=user.id,
            role=payload.role,
        )
        await self.repository.create_membership(db, created_membership)

        settings = get_settings()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=settings.invite_token_ttl_hours)
        await self.auth_repository.create_reset_token(
            db, PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        )

        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="user.invited",
            target_user_id=str(user.id),
            meta={"user_name": payload.name, "email": payload.email, "role": payload.role},
        )
        await db.commit()

        company = await self.company_repository.get_by_id(db, str(membership.company_id))
        company_name = company.name if company else "sua empresa"
        invite_url = f"{settings.frontend_url}/reset-password?token={token}"
        await self.email_service.send_user_invite(
            payload.email, invite_url, company_name, settings.invite_token_ttl_hours
        )

        target_membership = await self.repository.get_company_user(
            db, str(membership.company_id), str(user.id)
        )
        assert target_membership is not None
        return self.serialize_user(target_membership)

    async def update_user(
        self,
        db: AsyncSession,
        membership: Membership,
        user_id: str,
        payload: UserUpdateRequest,
    ) -> UserResponse:
        target_membership = await self.repository.get_company_user(
            db, str(membership.company_id), user_id
        )
        if target_membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado."
            )

        user_updates: dict[str, object] = {}
        if payload.name is not None:
            user_updates["name"] = payload.name
        if payload.password is not None:
            user_updates["password_hash"] = hash_password(payload.password)
        if payload.is_active is not None:
            user_updates["is_active"] = payload.is_active
        if user_updates:
            await self.repository.update_fields(db, target_membership.user, user_updates)

        if payload.role is not None:
            self.validate_role(payload.role)
            await self.repository.update_fields(db, target_membership, {"role": payload.role})

        await db.commit()
        updated_membership = await self.repository.get_company_user(
            db, str(membership.company_id), user_id
        )
        assert updated_membership is not None
        return self.serialize_user(updated_membership)

    async def list_revoked_users(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[UserRevokedItemResponse], PageMeta]:
        memberships, total = await self.repository.list_revoked_users_by_company(
            db, str(membership.company_id), params
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize_revoked(m) for m in memberships], meta

    async def reactivate_membership(
        self, db: AsyncSession, membership: Membership, user_id: str
    ) -> None:
        target = await self.repository.get_revoked_company_user(
            db, str(membership.company_id), user_id
        )
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership revogado nao encontrado.",
            )
        await self.membership_repository.reactivate(db, target)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="membership.reactivated",
            target_user_id=str(target.user_id),
            meta={"user_name": target.user.name, "role": target.role},
        )
        await db.commit()

    async def revoke_membership(
        self, db: AsyncSession, membership: Membership, user_id: str
    ) -> None:
        target_membership = await self.repository.get_company_user(
            db, str(membership.company_id), user_id
        )
        if target_membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado."
            )
        if str(target_membership.user_id) == str(membership.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Voce nao pode revogar o proprio acesso.",
            )
        await self.membership_repository.revoke(db, target_membership)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="membership.revoked",
            target_user_id=str(target_membership.user_id),
            meta={"user_name": target_membership.user.name, "role": target_membership.role},
        )
        await db.commit()

    @staticmethod
    def validate_role(role: str) -> None:
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role invalida.")

    @staticmethod
    def _serialize_revoked(membership: Membership) -> UserRevokedItemResponse:
        return UserRevokedItemResponse(
            id=str(membership.user.id),
            name=membership.user.name,
            email=membership.user.email,
            role=membership.role,
            revoked_at=membership.revoked_at.isoformat() if membership.revoked_at else "",
        )

    @staticmethod
    def serialize_user_list_item(membership: Membership) -> UserListItemResponse:
        return UserListItemResponse(
            id=str(membership.user.id),
            name=membership.user.name,
            email=membership.user.email,
            is_active=membership.user.is_active,
            role=membership.role,
        )

    @staticmethod
    def serialize_user(membership: Membership) -> UserResponse:
        return UserResponse(
            id=str(membership.user.id),
            name=membership.user.name,
            email=membership.user.email,
            is_active=membership.user.is_active,
            role=membership.role,
            company_id=str(membership.company_id),
        )
