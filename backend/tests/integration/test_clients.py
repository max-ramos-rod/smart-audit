from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_clients_create_list_detail_update_and_soft_delete(client, auth_headers):
    create_response = await client.post(
        "/api/v1/clients",
        headers=auth_headers,
        json={"name": "Transportadora Alfa"},
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["name"] == "Transportadora Alfa"
    assert created["is_active"] is True
    client_id = created["id"]

    list_response = await client.get("/api/v1/clients?page=1&page_size=10", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["data"]) == 1
    assert_pagination_meta(
        list_payload, total=1, page=1, page_size=10, has_next=False, total_pages=1
    )

    detail_response = await client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["name"] == "Transportadora Alfa"

    update_response = await client.patch(
        f"/api/v1/clients/{client_id}",
        headers=auth_headers,
        json={"name": "Transportadora Beta"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Transportadora Beta"

    delete_response = await client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    # soft delete: disappears from the active listing...
    active_list = await client.get("/api/v1/clients", headers=auth_headers)
    assert active_list.json()["data"] == []

    # ...but still exists in the database (visible when filtering inactive)
    inactive_list = await client.get("/api/v1/clients?is_active=false", headers=auth_headers)
    inactive = inactive_list.json()["data"]
    assert len(inactive) == 1
    assert inactive[0]["id"] == client_id
    assert inactive[0]["is_active"] is False

    # detail still resolves (soft deleted, not removed)
    detail_after = await client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert detail_after.status_code == 200


async def test_clients_write_blocked_for_inspector(client, inspector_headers):
    assert_problem(
        await client.post(
            "/api/v1/clients", headers=inspector_headers, json={"name": "Negada"}
        ),
        403,
        "Usuario sem permissao para executar esta acao.",
    )


async def test_clients_read_allowed_for_common_member(client, viewer_headers):
    response = await client.get("/api/v1/clients", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_clients_isolated_by_company(client, auth_headers, viewer_headers):
    client_id = (
        await client.post(
            "/api/v1/clients",
            headers=auth_headers,
            json={"name": "Cliente Isolado"},
        )
    ).json()["data"]["id"]

    assert_problem(
        await client.get(f"/api/v1/clients/{client_id}", headers=viewer_headers),
        404,
        "Cliente nao encontrado.",
    )


async def test_clients_get_nonexistent_returns_404(client, auth_headers):
    assert_problem(
        await client.get(
            "/api/v1/clients/00000000-0000-0000-0000-000000000000", headers=auth_headers
        ),
        404,
        "Cliente nao encontrado.",
    )


async def test_clients_requires_auth(client):
    assert_problem(
        await client.get("/api/v1/clients"),
        401,
        "Token de acesso nao informado.",
    )
