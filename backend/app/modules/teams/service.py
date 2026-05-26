from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.memberships import Membership
from app.db.models.teams import Team, TeamMember
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
    ) -> None:
        self.repository = repository or TeamRepository()
        self.membership_repository = membership_repository or MembershipRepository()

    def list_teams(
        self,
        db: Session,
        membership: Membership,
        params: PaginationParams,
    ) -> tuple[list[TeamListItemResponse], PageMeta]:
        teams, total = self.repository.list_by_company(db, str(membership.company_id), params)
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize_list_item(t) for t in teams], meta

    def get_team(self, db: Session, membership: Membership, team_id: str) -> TeamResponse:
        team = self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada.")
        return self._serialize(team)

    def create_team(
        self,
        db: Session,
        membership: Membership,
        payload: TeamCreateRequest,
    ) -> TeamResponse:
        team = Team(
            company_id=membership.company_id,
            name=payload.name,
            created_by=membership.user_id,
        )
        self.repository.create_team(db, team)
        db.commit()
        team = self.repository.get_with_members(db, str(team.id), str(membership.company_id))
        return self._serialize(team)

    def update_team(
        self,
        db: Session,
        membership: Membership,
        team_id: str,
        payload: TeamUpdateRequest,
    ) -> TeamResponse:
        team = self.repository.get_with_members(db, team_id, str(membership.company_id))
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada.")
        self.repository.update_fields(db, team, {"name": payload.name})
        db.commit()
        team = self.repository.get_with_members(db, team_id, str(membership.company_id))
        return self._serialize(team)

    def delete_team(self, db: Session, membership: Membership, team_id: str) -> None:
        team = self.repository.get(db, team_id)
        if team is None or str(team.company_id) != str(membership.company_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada.")
        self.repository.delete(db, team)
        db.commit()

    def add_member(
        self,
        db: Session,
        membership: Membership,
        team_id: str,
        payload: TeamMemberAddRequest,
    ) -> TeamResponse:
        team = self.repository.get(db, team_id)
        if team is None or str(team.company_id) != str(membership.company_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada.")

        target = self.membership_repository.get_by_user_and_company(
            db, payload.user_id, str(membership.company_id)
        )
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario nao pertence a esta empresa.",
            )

        existing = self.repository.get_member(db, team_id, payload.user_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario ja e membro desta equipe.",
            )

        member = TeamMember(team_id=team_id, user_id=payload.user_id)
        self.repository.create_member(db, member)
        db.commit()
        team = self.repository.get_with_members(db, team_id, str(membership.company_id))
        return self._serialize(team)

    def remove_member(
        self,
        db: Session,
        membership: Membership,
        team_id: str,
        user_id: str,
    ) -> TeamResponse:
        team = self.repository.get(db, team_id)
        if team is None or str(team.company_id) != str(membership.company_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipe nao encontrada.")

        member = self.repository.get_member(db, team_id, user_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario nao e membro desta equipe.",
            )

        self.repository.delete(db, member)
        db.commit()
        team = self.repository.get_with_members(db, team_id, str(membership.company_id))
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
