from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

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
async def list_teams(
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data, meta = await service.list_teams(db, membership, params)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
async def create_team(
    payload: TeamCreateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = await service.create_team(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = await service.get_team(db, membership, team_id)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    payload: TeamUpdateRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = await service.update_team(db, membership, team_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    await service.delete_team(db, membership, team_id)
    return success_response(None)


@router.post("/{team_id}/members")
async def add_member(
    team_id: str,
    payload: TeamMemberAddRequest,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = await service.add_member(db, membership, team_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    membership: Membership = Depends(get_manager_membership),
    db: AsyncSession = Depends(get_db),
    service: TeamService = Depends(get_team_service),
) -> dict[str, object]:
    data = await service.remove_member(db, membership, team_id, user_id)
    return success_response(data.model_dump(mode="json"))
