from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.memberships.permissions import get_admin_membership
from app.modules.users.schemas import UserCreateRequest, UserUpdateRequest
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service() -> UserService:
    return UserService()


@router.get("")
async def list_users(
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, object]:
    data, meta = await user_service.list_users(db, membership, params)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, object]:
    data = await user_service.get_user(db, membership, user_id)
    return success_response(data.model_dump(mode="json"))


@router.post("")
async def create_user(
    payload: UserCreateRequest,
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, object]:
    data = await user_service.create_user(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, object]:
    data = await user_service.update_user(db, membership, user_id, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/{user_id}")
async def revoke_user_membership(
    user_id: str,
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, object]:
    await user_service.revoke_membership(db, membership, user_id)
    return success_response(None)
