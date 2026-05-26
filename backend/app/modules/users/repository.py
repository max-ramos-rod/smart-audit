from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.companies import Company
from app.db.models.memberships import Membership
from app.db.models.users import User


class UserRepository(SQLAlchemyRepository[User]):
    model = User

    def list_users_by_company(self, db: Session, company_id: str, params: PaginationParams) -> tuple[list[Membership], int]:
        statement = (
            select(Membership)
            .where(Membership.company_id == company_id)
            .options(selectinload(Membership.user), selectinload(Membership.company))
            .order_by(User.name.asc())
            .join(Membership.user)
        )
        return self._paginate_select(db, statement, params)

    def get_company_user(self, db: Session, company_id: str, user_id: str) -> Membership | None:
        statement = (
            select(Membership)
            .where(Membership.company_id == company_id, Membership.user_id == user_id)
            .options(selectinload(Membership.user), selectinload(Membership.company))
        )
        return self._get_one(db, statement)

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self._get_one(db, statement)

    def create_user(self, db: Session, user: User) -> User:
        return self._save(db, user)

    def create_membership(self, db: Session, membership: Membership) -> Membership:
        return self._save(db, membership)

    def get_company_by_id(self, db: Session, company_id: str) -> Company | None:
        statement = select(Company).where(Company.id == company_id)
        return self._get_one(db, statement)
