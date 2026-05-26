from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, dict[str, str]]:
    return {
        "data": {
            "status": "ok",
            "service": "smart-audit-api",
        },
        "meta": {},
    }
