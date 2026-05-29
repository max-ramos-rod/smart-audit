from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.responses import success_response
from app.db.session import get_db
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.schemas import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest
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
    return success_response(token.model_dump())


@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    response = auth_service.serialize_user(current_user)
    return success_response(response.model_dump())


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    await auth_service.request_password_reset(db, payload.email)
    return success_response({"message": "Se o e-mail existir, um link sera enviado."})


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, object]:
    await auth_service.reset_password(db, payload.token, payload.new_password)
    return success_response({"message": "Senha redefinida com sucesso."})
