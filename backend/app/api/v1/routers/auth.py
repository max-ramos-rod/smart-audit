from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db.session import get_db
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    token = await auth_service.login(db, payload.email, payload.password)
    return {
        "data": token.model_dump(),
        "meta": {},
    }


@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    response = auth_service.serialize_user(current_user)
    return {
        "data": response.model_dump(),
        "meta": {},
    }
