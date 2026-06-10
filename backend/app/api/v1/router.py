from fastapi import APIRouter

from app.api.v1.routers.asset_types import router as asset_types_router
from app.api.v1.routers.attachments import router as attachments_router
from app.api.v1.routers.audit_logs import router as audit_logs_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.clients import router as clients_router
from app.api.v1.routers.companies import router as companies_router
from app.api.v1.routers.forms import router as forms_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.me import router as me_router
from app.api.v1.routers.search import router as search_router
from app.api.v1.routers.submissions import router as submissions_router
from app.api.v1.routers.teams import router as teams_router
from app.api.v1.routers.uploads import router as uploads_router
from app.api.v1.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(clients_router)
api_router.include_router(asset_types_router)
api_router.include_router(me_router)
api_router.include_router(users_router)
api_router.include_router(forms_router)
api_router.include_router(submissions_router)
api_router.include_router(teams_router)
api_router.include_router(attachments_router)
api_router.include_router(uploads_router)
api_router.include_router(search_router)
api_router.include_router(audit_logs_router)
