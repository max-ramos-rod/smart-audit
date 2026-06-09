from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_audit_logs_records_user_created(client, auth_headers, seeded_user):
    """Criar um usuario gera um evento user.created legivel em GET /audit-logs."""
    create_response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Auditada",
            "email": "auditada@smartaudit.local",
            "password": "auditada123",
            "role": "VIEWER",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    created_id = create_response.json()["data"]["id"]

    response = await client.get("/api/v1/audit-logs?page=1&page_size=20", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert_pagination_meta(payload, total=1, page=1, page_size=20, has_next=False, total_pages=1)

    entry = payload["data"][0]
    assert entry["action"] == "user.created"
    assert entry["company_id"] == seeded_user["company_id"]
    assert entry["actor_id"] == seeded_user["user_id"]
    assert entry["target_user_id"] == created_id
    assert entry["meta"]["email"] == "auditada@smartaudit.local"
    assert entry["meta"]["role"] == "VIEWER"
    assert entry["created_at"]


async def test_audit_logs_filter_by_action(client, auth_headers):
    """O filtro ?action= retorna apenas eventos da acao pedida."""
    create_response = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "name": "Para Revogar",
            "email": "para.revogar@smartaudit.local",
            "password": "revogar123",
            "role": "INSPECTOR",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    target_id = create_response.json()["data"]["id"]

    revoke_response = await client.delete(f"/api/v1/users/{target_id}", headers=auth_headers)
    assert revoke_response.status_code == 200

    # Sem filtro: dois eventos (user.created + membership.revoked).
    all_response = await client.get("/api/v1/audit-logs", headers=auth_headers)
    assert all_response.status_code == 200
    actions = {entry["action"] for entry in all_response.json()["data"]}
    assert actions == {"user.created", "membership.revoked"}

    # Com filtro: apenas a acao pedida.
    filtered = await client.get(
        "/api/v1/audit-logs?action=membership.revoked", headers=auth_headers
    )
    assert filtered.status_code == 200
    data = filtered.json()["data"]
    assert len(data) == 1
    assert data[0]["action"] == "membership.revoked"
    assert data[0]["target_user_id"] == target_id


async def test_audit_logs_require_admin_role(client, inspector_headers):
    """INSPECTOR nao tem acesso ao log de auditoria (requer ADMIN ou superior)."""
    response = await client.get("/api/v1/audit-logs", headers=inspector_headers)
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_audit_logs_company_isolation(client, multi_company_user):
    """Logs de uma empresa nao vazam para outra empresa do mesmo usuario."""
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": multi_company_user["email"],
            "password": multi_company_user["password"],
        },
    )
    token = login.json()["data"]["access_token"]
    headers_a = {
        "Authorization": f"Bearer {token}",
        "X-Company-Id": multi_company_user["company_a_id"],
    }
    headers_b = {
        "Authorization": f"Bearer {token}",
        "X-Company-Id": multi_company_user["company_b_id"],
    }

    # Gera um evento na empresa A.
    create_response = await client.post(
        "/api/v1/users",
        headers=headers_a,
        json={
            "name": "So Empresa A",
            "email": "so.empresa.a@smartaudit.local",
            "password": "empresaA123",
            "role": "VIEWER",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200

    # A empresa B nao enxerga o log da empresa A.
    response_b = await client.get("/api/v1/audit-logs", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json()["data"] == []

    # A empresa A enxerga o proprio log.
    response_a = await client.get("/api/v1/audit-logs", headers=headers_a)
    assert response_a.status_code == 200
    data_a = response_a.json()["data"]
    assert len(data_a) == 1
    assert data_a[0]["company_id"] == multi_company_user["company_a_id"]
