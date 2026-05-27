from backend.tests.integration.test_auth import assert_problem


async def test_get_my_company_returns_company_data(client, auth_headers, seeded_user):
    response = await client.get("/api/v1/companies/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == seeded_user["company_id"]
    assert "name" in data
    assert "slug" in data
    assert "plan" in data
    assert "is_active" in data


async def test_get_my_company_requires_auth(client):
    response = await client.get("/api/v1/companies/me")
    assert_problem(response, 401, "Token de acesso nao informado.")


async def test_patch_my_company_updates_fields(client, auth_headers):
    payload = {
        "cnpj": "12.345.678/0001-99",
        "timezone": "America/Manaus",
        "contact_email": "contato@empresa.test",
        "phone": "+55 92 9999-0000",
    }
    response = await client.patch("/api/v1/companies/me", headers=auth_headers, json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cnpj"] == "12.345.678/0001-99"
    assert data["timezone"] == "America/Manaus"
    assert data["contact_email"] == "contato@empresa.test"
    assert data["phone"] == "+55 92 9999-0000"

    verify = await client.get("/api/v1/companies/me", headers=auth_headers)
    assert verify.status_code == 200
    verify_data = verify.json()["data"]
    assert verify_data["cnpj"] == "12.345.678/0001-99"
    assert verify_data["timezone"] == "America/Manaus"


async def test_patch_my_company_updates_name(client, auth_headers):
    response = await client.patch(
        "/api/v1/companies/me",
        headers=auth_headers,
        json={"name": "Empresa Renomeada"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Empresa Renomeada"


async def test_patch_my_company_ignores_empty_payload(client, auth_headers):
    get_before = await client.get("/api/v1/companies/me", headers=auth_headers)
    name_before = get_before.json()["data"]["name"]

    response = await client.patch("/api/v1/companies/me", headers=auth_headers, json={})
    assert response.status_code == 200
    assert response.json()["data"]["name"] == name_before


async def test_patch_my_company_requires_admin_role(client, inspector_headers):
    response = await client.patch(
        "/api/v1/companies/me",
        headers=inspector_headers,
        json={"contact_email": "hacker@evil.test"},
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_patch_my_company_requires_auth(client):
    response = await client.patch("/api/v1/companies/me", json={"name": "Sem token"})
    assert_problem(response, 401, "Token de acesso nao informado.")
