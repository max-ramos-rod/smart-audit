from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.session import get_db
from app.modules.memberships.dependencies import get_current_membership
from app.modules.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service() -> SearchService:
    return SearchService()


@router.get("")
async def search(
    q: str = Query(min_length=2, max_length=100),
    membership=Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
) -> dict[str, object]:
    data = await search_service.search(db, str(membership.company_id), q)
    return success_response(data.model_dump(mode="json"))
