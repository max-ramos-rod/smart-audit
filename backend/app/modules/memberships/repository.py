from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.repositories import SQLAlchemyRepository
from app.db.models.memberships import Membership


class MembershipRepository(SQLAlchemyRepository[Membership]):
    model = Membership

    def list_by_user_id(self, db: Session, user_id: str) -> list[Membership]:
        statement = select(Membership).where(Membership.user_id == user_id)
        return self._list_from_stmt(db, statement)

    def get_by_user_and_company(self, db: Session, user_id: str, company_id: str) -> Membership | None:
        statement = select(Membership).where(
            Membership.user_id == user_id,
            Membership.company_id == company_id,
        )
        return self._get_one(db, statement)
