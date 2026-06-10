from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_asset_types_crud_and_soft_delete(client, auth_headers):
    create_response = await client.post(
        "/api/v1/asset-types",
        headers=auth_headers,
        json={"name": "Veiculo", "description": "Frota rodoviaria"},
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["name"] == "Veiculo"
    assert created["description"] == "Frota rodoviaria"
    assert created["attributes_schema"] is None
    assert created["is_active"] is True
    type_id = created["id"]

    list_response = await client.get(
        "/api/v1/asset-types?page=1&page_size=10", headers=auth_headers
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["data"]) == 1
    assert_pagination_meta(
        list_payload, total=1, page=1, page_size=10, has_next=False, total_pages=1
    )

    detail_response = await client.get(f"/api/v1/asset-types/{type_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["name"] == "Veiculo"

    update_response = await client.patch(
        f"/api/v1/asset-types/{type_id}",
        headers=auth_headers,
        json={"name": "Veiculo Pesado", "description": None},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["name"] == "Veiculo Pesado"
    assert updated["description"] is None

    delete_response = await client.delete(
        f"/api/v1/asset-types/{type_id}", headers=auth_headers
    )
    assert delete_response.status_code == 200

    # soft delete: gone from the active listing, still in the database
    assert (await client.get("/api/v1/asset-types", headers=auth_headers)).json()["data"] == []
    inactive = (
        await client.get("/api/v1/asset-types?is_active=false", headers=auth_headers)
    ).json()["data"]
    assert len(inactive) == 1
    assert inactive[0]["id"] == type_id
    assert inactive[0]["is_active"] is False


async def test_asset_types_attributes_schema_accepted_free(client, auth_headers):
    # M1: attributes_schema is accepted as free JSON, with NO content validation.
    arbitrary_schema = {
        "anything": ["goes", "here"],
        "nested": {"max_speed": {"type": "number"}, "color": {"enum": [1, 2, 3]}},
        "not_a_real_json_schema": True,
    }
    created = (
        await client.post(
            "/api/v1/asset-types",
            headers=auth_headers,
            json={"name": "Bomba", "attributes_schema": arbitrary_schema},
        )
    ).json()["data"]
    assert created["attributes_schema"] == arbitrary_schema

    # ...and creating a type WITHOUT a schema is equally valid.
    without = (
        await client.post(
            "/api/v1/asset-types",
            headers=auth_headers,
            json={"name": "Motor"},
        )
    )
    assert without.status_code == 200
    assert without.json()["data"]["attributes_schema"] is None


async def test_asset_types_write_blocked_for_inspector(client, inspector_headers):
    assert_problem(
        await client.post(
            "/api/v1/asset-types", headers=inspector_headers, json={"name": "Negada"}
        ),
        403,
        "Usuario sem permissao para executar esta acao.",
    )


async def test_asset_types_read_allowed_for_common_member(client, viewer_headers):
    response = await client.get("/api/v1/asset-types", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_asset_types_isolated_by_company(client, auth_headers, viewer_headers):
    type_id = (
        await client.post(
            "/api/v1/asset-types",
            headers=auth_headers,
            json={"name": "Tipo Isolado"},
        )
    ).json()["data"]["id"]

    assert_problem(
        await client.get(f"/api/v1/asset-types/{type_id}", headers=viewer_headers),
        404,
        "Tipo de ativo nao encontrado.",
    )


async def test_asset_types_get_nonexistent_returns_404(client, auth_headers):
    assert_problem(
        await client.get(
            "/api/v1/asset-types/00000000-0000-0000-0000-000000000000", headers=auth_headers
        ),
        404,
        "Tipo de ativo nao encontrado.",
    )


async def test_asset_types_requires_auth(client):
    assert_problem(
        await client.get("/api/v1/asset-types"),
        401,
        "Token de acesso nao informado.",
    )
