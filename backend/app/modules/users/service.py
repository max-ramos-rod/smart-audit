from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.core.security import hash_password
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreateRequest,
    UserListItemResponse,
    UserResponse,
    UserUpdateRequest,
)

ALLOWED_ROLES = {"OWNER", "ADMIN", "MANAGER", "INSPECTOR", "VIEWER"}


class UserService:
    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    def list_users(
        self,
        db: Session,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[UserListItemResponse], PageMeta]:
        memberships, total = self.repository.list_users_by_company(db, str(membership.company_id), params)
        meta = PaginationMetaBuilder.build(total, params)
        return [self.serialize_user_list_item(item) for item in memberships], meta

    def get_user(self, db: Session, membership: Membership, user_id: str) -> UserResponse:
        target_membership = self.repository.get_company_user(db, str(membership.company_id), user_id)
        if target_membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
        return self.serialize_user(target_membership)

    def create_user(self, db: Session, membership: Membership, payload: UserCreateRequest) -> UserResponse:
        self.validate_role(payload.role)

        existing_user = self.repository.get_user_by_email(db, payload.email)
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ja existe usuario com esse email.")

        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            is_active=payload.is_active,
        )
        self.repository.create_user(db, user)

        created_membership = Membership(
            company_id=membership.company_id,
            user_id=user.id,
            role=payload.role,
        )
        self.repository.create_membership(db, created_membership)
        db.commit()

        target_membership = self.repository.get_company_user(db, str(membership.company_id), str(user.id))
        return self.serialize_user(target_membership)

    def update_user(
        self,
        db: Session,
        membership: Membership,
        user_id: str,
        payload: UserUpdateRequest,
    ) -> UserResponse:
        target_membership = self.repository.get_company_user(db, str(membership.company_id), user_id)
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
            self.repository.update_fields(db, target_membership.user, user_updates)

        if payload.role is not None:
            self.validate_role(payload.role)
            self.repository.update_fields(db, target_membership, {"role": payload.role})

        db.commit()
        updated_membership = self.repository.get_company_user(db, str(membership.company_id), user_id)
        return self.serialize_user(updated_membership)

    @staticmethod
    def validate_role(role: str) -> None:
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role invalida.")

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
