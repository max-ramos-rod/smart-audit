from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette import status as http_status

PROBLEM_JSON = "application/problem+json"


STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
}



def build_problem(
    request: Request,
    *,
    status_code: int,
    title: str | None = None,
    detail: str,
    type_: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": type_,
        "title": title or STATUS_TITLES.get(status_code, "Error"),
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if extra:
        payload.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type=PROBLEM_JSON,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Erro na requisicao."
    return build_problem(request, status_code=exc.status_code, detail=detail)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return build_problem(
        request,
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Unprocessable Entity",
        detail="A requisicao contem dados invalidos.",
        type_="https://smart-audit/errors/validation-error",
        extra={"errors": exc.errors()},
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return build_problem(
        request,
        status_code=429,
        title="Too Many Requests",
        detail="Limite de requisicoes excedido. Tente novamente em breve.",
        type_="https://smart-audit/errors/rate-limit-exceeded",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return build_problem(
        request,
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Ocorreu um erro interno no servidor.",
        type_="https://smart-audit/errors/internal-server-error",
    )
