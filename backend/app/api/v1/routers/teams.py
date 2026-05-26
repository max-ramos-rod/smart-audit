from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_manager_membership
from app.modules.teams.schemas import TeamCreateRequest, TeamMemberAddRequest, TeamUpdateRequest
from app.modules.teams.service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


def get_team_service() -> TeamService:
    return TeamService()


@router.get("")
def list_teams(
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data, meta = service.list_teams(db, membership, params)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
def create_team(
    payload: TeamCreateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = service.create_team(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{team_id}")
def get_team(
    team_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = service.get_team(db, membership, team_id)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{team_id}")
def update_team(
    team_id: str,
    payload: TeamUpdateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = service.update_team(db, membership, team_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{team_id}")
def delete_team(
    team_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    service.delete_team(db, membership, team_id)
    return success_response(None)


@router.post("/{team_id}/members")
def add_member(
    team_id: str,
    payload: TeamMemberAddRequest,
    membership: Membership = Depends(get_manager_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = service.add_member(db, membership, team_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{team_id}/members/{user_id}")
def remove_member(
    team_id: str,
    user_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: Session = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = service.remove_member(db, membership, team_id, user_id)
    return success_response(data.model_dump(mode="json"))
