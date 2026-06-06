from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_users_create_list_detail_and_update(client, auth_headers):
    create_response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Maria Gestora",
            "email": "maria.gestora@smartaudit.local",
            "password": "maria12345",
            "role": "MANAGER",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    created_payload = create_response.json()["data"]
    assert created_payload["name"] == "Maria Gestora"
    assert created_payload["role"] == "MANAGER"
    user_id = created_payload["id"]

    list_response = await client.get("/api/v1/users?page=1&page_size=10", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["data"]) == 2
    assert_pagination_meta(
        list_payload,
        total=2,
        page=1,
        page_size=10,
        has_next=False,
        total_pages=1,
    )

    detail_response = await client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["data"]
    assert detail_payload["email"] == "maria.gestora@smartaudit.local"

    update_response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
        json={
            "name": "Maria Supervisora",
            "role": "ADMIN",
            "is_active": False,
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()["data"]
    assert updated_payload["name"] == "Maria Supervisora"
    assert updated_payload["role"] == "ADMIN"
    assert updated_payload["is_active"] is False


async def test_users_reject_duplicate_email(client, auth_headers):
    first_response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Usuario Unico",
            "email": "usuario.unico@smartaudit.local",
            "password": "usuario123",
            "role": "VIEWER",
            "is_active": True,
        },
    )
    assert first_response.status_code == 200

    second_response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Usuario Duplicado",
            "email": "usuario.unico@smartaudit.local",
            "password": "usuario123",
            "role": "VIEWER",
            "is_active": True,
        },
    )
    assert_problem(second_response, 400, "Ja existe usuario com esse email.")


async def test_users_require_admin_role(client, inspector_headers):
    response = await client.get("/api/v1/users", headers=inspector_headers)
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_invite_user_flow(client, auth_headers):
    """Convite cria o usuario sem senha; o convidado define a senha pelo link e loga."""
    import io
    import logging

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("app.core.email.sender")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    invite_response = await client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={"name": "Convidado", "email": "convidado@smartaudit.local", "role": "INSPECTOR"},
    )
    logger.removeHandler(handler)
    assert invite_response.status_code == 200
    assert invite_response.json()["data"]["role"] == "INSPECTOR"

    # Antes de definir a senha, o convidado nao consegue logar.
    early_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "convidado@smartaudit.local", "password": "qualquer-coisa"},
    )
    assert early_login.status_code == 401

    # Extrai o token do link de convite logado.
    token = None
    for line in log_stream.getvalue().splitlines():
        if "reset-password?token=" in line:
            token = line.split("token=")[-1].strip()
            break
    assert token, "Token de convite nao encontrado no log"

    # Define a senha pelo mesmo endpoint do reset.
    new_password = "ConvidadoSenha@2026"
    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_response.status_code == 200

    # Agora o convidado loga normalmente.
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "convidado@smartaudit.local", "password": new_password},
    )
    assert login_response.status_code == 200


async def test_invite_user_rejects_duplicate_email(client, auth_headers, seeded_user):
    response = await client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={"name": "Dup", "email": seeded_user["email"], "role": "VIEWER"},
    )
    assert_problem(response, 400, "Ja existe usuario com esse email.")
