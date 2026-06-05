from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.memberships import Membership
from app.db.models.teams import Team, TeamMember
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.memberships.repository import MembershipRepository
from app.modules.teams.repository import TeamRepository
from app.modules.teams.schemas import (
    TeamCreateRequest,
    TeamListItemResponse,
    TeamMemberAddRequest,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdateRequest,
)


class TeamService:
    def __init__(
        self,
        repository: TeamRepository | None = None,
        membership_repository: MembershipRepository | None = None,
        audit_repository: AuditLogRepository | None = None,
    ) -> None:
        self.repository = repository or TeamRepository()
        self.membership_repository = membership_repository or MembershipRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    async def list_teams(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[TeamListItemResponse], PageMeta]:
        teams, total = await self.repository.list_by_company(
            db, str(membership.company_id), params
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize_list_item(t) for t in teams], meta

    async def get_team(
        self, db: AsyncSession, membership: Membership, team_id: str
    ) -> TeamResponse:
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada."
            )
        return self._serialize(team)

    async def create_team(
        self,
        db: AsyncSession,
        membership: Membership,
        payload: TeamCreateRequest,
    ) -> TeamResponse:
        team = Team(
            company_id=membership.company_id,
            name=payload.name,
            created_by=membership.user_id,
        )
        await self.repository.create_team(db, team)
        await db.commit()
        team = await self.repository.get_with_members(db, str(team.id), str(membership.company_id))
        return self._serialize(team)

    async def update_team(
        self,
        db: AsyncSession,
        membership: Membership,
        team_id: str,
        payload: TeamUpdateRequest,
    ) -> TeamResponse:
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada."
            )
        await self.repository.update_fields(db, team, {"name": payload.name})
        await db.commit()
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        return self._serialize(team)

    async def deactivate_team(
        self, db: AsyncSession, membership: Membership, team_id: str
    ) -> None:
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada."
            )
        await self.repository.deactivate(db, team)
        await self.audit_repository.log(
            db,
            company_id=str(membership.company_id),
            actor_id=str(membership.user_id),
            action="team.deactivated",
            meta={"team_name": team.name},
        )
        await db.commit()

    async def add_member(
        self,
        db: AsyncSession,
        membership: Membership,
        team_id: str,
        payload: TeamMemberAddRequest,
    ) -> TeamResponse:
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada."
            )

        target = await self.membership_repository.get_by_user_and_company(
            db, payload.user_id, str(membership.company_id)
        )
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario nao pertence a esta empresa.",
            )

        existing = await self.repository.get_member(db, team_id, payload.user_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario ja e membro desta equipe.",
            )

        member = TeamMember(team_id=team_id, user_id=payload.user_id)
        await self.repository.create_member(db, member)
        await db.commit()
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        return self._serialize(team)

    async def remove_member(
        self,
        db: AsyncSession,
        membership: Membership,
        team_id: str,
        user_id: str,
    ) -> TeamResponse:
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada."
            )

        member = await self.repository.get_member(db, team_id, user_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario nao e membro desta equipe.",
            )

        await self.repository.delete(db, member)
        await db.commit()
        team = await self.repository.get_with_members(db, team_id, str(membership.company_id))
        return self._serialize(team)

    @staticmethod
    def _serialize(team: Team) -> TeamResponse:
        return TeamResponse(
            id=str(team.id),
            company_id=str(team.company_id),
            name=team.name,
            members=[
                TeamMemberResponse(
                    user_id=str(m.user_id),
                    name=m.user.name,
                    email=m.user.email,
                )
                for m in team.members
            ],
        )

    @staticmethod
    def _serialize_list_item(team: Team) -> TeamListItemResponse:
        return TeamListItemResponse(
            id=str(team.id),
            company_id=str(team.company_id),
            name=team.name,
            member_count=len(team.members),
        )
