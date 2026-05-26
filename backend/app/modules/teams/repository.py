from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.teams import Team, TeamMember


class TeamRepository(SQLAlchemyRepository[Team]):
    model = Team

    def list_by_company(
        self,
        db: Session,
        company_id: str,
        params: PaginationParams,
    ) -> tuple[list[Team], int]:
        statement = (
            select(Team)
            .where(Team.company_id == company_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
            .order_by(Team.name)
        )
        return self._paginate_select(db, statement, params, unique=True)

    def get_with_members(self, db: Session, team_id: str, company_id: str) -> Team | None:
        statement = (
            select(Team)
            .where(Team.id == team_id, Team.company_id == company_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        return self._get_one(db, statement)

    def get_member(self, db: Session, team_id: str, user_id: str) -> TeamMember | None:
        statement = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        return self._get_one(db, statement)

    def create_team(self, db: Session, team: Team) -> Team:
        return self._save(db, team)

    def create_member(self, db: Session, member: TeamMember) -> TeamMember:
        return self._save(db, member)
