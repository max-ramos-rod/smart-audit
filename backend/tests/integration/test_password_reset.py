"""Integration tests for POST /auth/forgot-password and POST /auth/reset-password."""
from backend.tests.integration.test_auth import assert_problem


async def test_forgot_password_always_returns_200(client, seeded_user):
    """Returns 200 regardless of whether the email exists (don't reveal enumeration)."""
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": seeded_user["email"]},
    )
    assert response.status_code == 200
    assert "message" in response.json()["data"]


async def test_forgot_password_unknown_email_still_200(client):
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ninguem@exemplo.com"},
    )
    assert response.status_code == 200


async def test_forgot_password_empty_email_returns_422(client):
    response = await client.post("/api/v1/auth/forgot-password", json={"email": ""})
    assert response.status_code == 422


async def _get_reset_token(client, seeded_user, capfd=None) -> str:
    """Request a reset and capture the token from the log output."""
    import logging
    import io

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("app.modules.auth.service")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": seeded_user["email"]},
    )

    logger.removeHandler(handler)
    log_output = log_stream.getvalue()

    # log line: "PASSWORD RESET | email=... | url=.../reset-password?token=<token>"
    for line in log_output.splitlines():
        if "reset-password?token=" in line:
            return line.split("token=")[-1].strip()

    raise AssertionError(f"Reset token not found in log output: {log_output!r}")


async def test_reset_password_flow(client, seeded_user):
    """Full happy path: request reset → use token → login with new password."""
    token = await _get_reset_token(client, seeded_user)

    new_password = "NovaSenha@2026"
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()["data"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user["email"], "password": new_password},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()["data"]


async def test_reset_token_cannot_be_reused(client, seeded_user):
    token = await _get_reset_token(client, seeded_user)

    await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "PrimeiraSenha@2026"},
    )

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "SegundaSenha@2026"},
    )
    assert_problem(resp, 400, "Token invalido ou expirado.")


async def test_reset_invalid_token_returns_400(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "token-que-nao-existe", "new_password": "SenhaValida@2026"},
    )
    assert_problem(resp, 400, "Token invalido ou expirado.")


async def test_reset_password_too_short_returns_422(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "qualquer", "new_password": "123"},
    )
    assert resp.status_code == 422
