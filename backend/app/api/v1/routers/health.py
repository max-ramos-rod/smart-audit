from fastapi import APIRouter

from app.core.responses import success_response

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, object]:
    return success_response({"status": "ok", "service": "smart-audit-api"})
