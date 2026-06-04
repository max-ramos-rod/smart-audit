from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.teams import Team, TeamMember


class TeamRepository(SQLAlchemyRepository[Team]):
    model = Team

    async def list_by_company(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
    ) -> tuple[list[Team], int]:
        statement = (
            select(Team)
            .where(Team.company_id == company_id, Team.is_active.is_(True))
            .options(selectinload(Team.members).selectinload(TeamMember.user))
            .order_by(Team.name)
        )
        return await self._paginate_select(db, statement, params, unique=True)

    async def get_with_members(
        self, db: AsyncSession, team_id: str, company_id: str
    ) -> Team | None:
        statement = (
            select(Team)
            .where(Team.id == team_id, Team.company_id == company_id, Team.is_active.is_(True))
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        return await self._get_one(db, statement)

    async def get_member(
        self, db: AsyncSession, team_id: str, user_id: str
    ) -> TeamMember | None:
        statement = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        return await self._get_one(db, statement)

    async def create_team(self, db: AsyncSession, team: Team) -> Team:
        return await self._save(db, team)

    async def create_member(self, db: AsyncSession, member: TeamMember) -> TeamMember:
        return await self._save(db, member)

    async def deactivate(self, db: AsyncSession, team: Team) -> None:
        team.is_active = False
        await self._save(db, team)
