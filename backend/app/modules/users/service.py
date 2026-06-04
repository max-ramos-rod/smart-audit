from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.core.security import hash_password
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.memberships.repository import MembershipRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreateRequest,
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
    ) -> None:
        self.repository = repository or UserRepository()
        self.membership_repository = membership_repository or MembershipRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
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
            revoked_at=membership.revoked_at.isoformat(),
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
