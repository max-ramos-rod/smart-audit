from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.memberships import Membership
from app.db.models.users import User
from app.modules.auth.schemas import AuthenticatedUserResponse
from app.modules.auth.service import AuthService
from app.modules.memberships.repository import MembershipRepository
from app.modules.memberships.schemas import (
    MembershipContextResponse,
    UserCompanyResponse,
    UserContextResponse,
)


class MembershipService:
    def __init__(self, repository: MembershipRepository | None = None) -> None:
        self.repository = repository or MembershipRepository()

    def list_user_companies(self, db: Session, user: User) -> list[UserCompanyResponse]:
        memberships = self.repository.list_by_user_id(db, str(user.id))
        return [self.serialize_company(membership) for membership in memberships]

    def get_user_context(
        self,
        db: Session,
        user: User,
        company_id: str | None = None,
    ) -> UserContextResponse:
        memberships = self.repository.list_by_user_id(db, str(user.id))
        if not memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem empresa vinculada.",
            )

        selected_membership = self.resolve_membership(memberships, company_id)
        requires_company_selection = company_id is None and len(memberships) > 1

        return UserContextResponse(
            user=AuthService.serialize_user(user),
            active_company=self.serialize_company(selected_membership) if selected_membership else None,
            membership=MembershipContextResponse(role=selected_membership.role) if selected_membership else None,
            available_companies=[self.serialize_company(membership) for membership in memberships],
            requires_company_selection=requires_company_selection,
        )

    @staticmethod
    def resolve_membership(
        memberships: list[Membership],
        company_id: str | None,
    ) -> Membership | None:
        if company_id:
            membership = next((item for item in memberships if str(item.company_id) == company_id), None)
            if membership is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario sem acesso a empresa informada.",
                )
            return membership

        if len(memberships) == 1:
            return memberships[0]

        return None

    @staticmethod
    def serialize_company(membership: Membership) -> UserCompanyResponse:
        company = membership.company
        return UserCompanyResponse(
            id=str(company.id),
            name=company.name,
            slug=company.slug,
            plan=company.plan,
            role=membership.role,
            is_active=company.is_active,
        )
