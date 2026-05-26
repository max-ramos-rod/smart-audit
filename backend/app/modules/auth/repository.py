from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.repositories import SQLAlchemyRepository
from app.db.models.users import User


class AuthRepository(SQLAlchemyRepository[User]):
    model = User

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self._get_one(db, statement)

    def get_user_by_id(self, db: Session, user_id: str) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self._get_one(db, statement)
