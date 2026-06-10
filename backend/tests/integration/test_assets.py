from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def _login(client, user) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _headers(token: str, company_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Company-Id": company_id}


async def _create_type(client, headers, name: str = "Veiculo") -> str:
    response = await client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert response.status_code == 200
    return response.json()["data"]["id"]


async def _create_client(client, headers, name: str = "Cliente Alfa") -> str:
    response = await client.post("/api/v1/clients", headers=headers, json={"name": name})
    assert response.status_code == 200
    return response.json()["data"]["id"]


async def _create_asset(client, headers, **payload) -> dict:
    response = await client.post("/api/v1/assets", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_assets_create_root_and_component_tree(client, auth_headers):
    type_id = await _create_type(client, auth_headers)

    root = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Caminhao 01"
    )
    assert root["parent_asset_id"] is None
    assert root["status"] == "active"
    assert root["components"] == []

    component = await _create_asset(
        client,
        auth_headers,
        asset_type_id=type_id,
        identifier="Roda Dianteira Direita",
        parent_asset_id=root["id"],
    )
    assert component["parent_asset_id"] == root["id"]

    # depth >= 2: a component of the component (CA2)
    grandchild = await _create_asset(
        client,
        auth_headers,
        asset_type_id=type_id,
        identifier="Parafuso 5",
        parent_asset_id=component["id"],
    )

    root_detail = (
        await client.get(f"/api/v1/assets/{root['id']}", headers=auth_headers)
    ).json()["data"]
    assert [c["id"] for c in root_detail["components"]] == [component["id"]]

    component_detail = (
        await client.get(f"/api/v1/assets/{component['id']}", headers=auth_headers)
    ).json()["data"]
    assert [c["id"] for c in component_detail["components"]] == [grandchild["id"]]


async def test_assets_two_domains_share_schema(client, auth_headers):
    # CA1: two asset types from different domains, no schema change required.
    vehicle_type = await _create_type(client, auth_headers, name="Veiculo")
    building_type = await _create_type(client, auth_headers, name="Predio")

    vehicle = await _create_asset(
        client, auth_headers, asset_type_id=vehicle_type, identifier="Van 02"
    )
    building = await _create_asset(
        client, auth_headers, asset_type_id=building_type, identifier="Sede Central"
    )
    assert vehicle["asset_type_id"] == vehicle_type
    assert building["asset_type_id"] == building_type


async def test_assets_attributes_json_accepted_free(client, auth_headers):
    # M1: attributes_json is stored verbatim, no validation.
    type_id = await _create_type(client, auth_headers)
    attrs = {"placa": "ABC-1234", "specs": {"eixos": 3, "tags": ["a", "b"]}}
    asset = await _create_asset(
        client,
        auth_headers,
        asset_type_id=type_id,
        identifier="Carreta 9",
        attributes_json=attrs,
    )
    assert asset["attributes_json"] == attrs


async def test_assets_client_only_on_root(client, auth_headers):
    # CA4/M6: client_id allowed on a root, rejected on a component.
    type_id = await _create_type(client, auth_headers)
    client_id = await _create_client(client, auth_headers)

    root = await _create_asset(
        client,
        auth_headers,
        asset_type_id=type_id,
        identifier="Frota do Cliente",
        client_id=client_id,
    )
    assert root["client_id"] == client_id

    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "asset_type_id": type_id,
                "identifier": "Componente com cliente",
                "parent_asset_id": root["id"],
                "client_id": client_id,
            },
        ),
        400,
        "client_id so e permitido em ativo raiz.",
    )


async def test_assets_foreign_references_rejected(client, multi_company_user):
    # CA4/V1: asset_type_id / client_id from another company are rejected.
    token = await _login(client, multi_company_user)
    headers_a = _headers(token, multi_company_user["company_a_id"])
    headers_b = _headers(token, multi_company_user["company_b_id"])

    foreign_type = await _create_type(client, headers_b, name="Tipo da Empresa B")
    foreign_client = await _create_client(client, headers_b, name="Cliente da Empresa B")
    local_type = await _create_type(client, headers_a, name="Tipo da Empresa A")

    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=headers_a,
            json={"asset_type_id": foreign_type, "identifier": "Tipo estrangeiro"},
        ),
        400,
        "Tipo de ativo invalido.",
    )

    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=headers_a,
            json={
                "asset_type_id": local_type,
                "identifier": "Cliente estrangeiro",
                "client_id": foreign_client,
            },
        ),
        400,
        "Cliente invalido.",
    )


async def test_assets_patch_parent_is_immutable(client, auth_headers):
    # M5/V2: parent_asset_id cannot be changed after creation.
    type_id = await _create_type(client, auth_headers)
    root = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Raiz"
    )
    component = await _create_asset(
        client,
        auth_headers,
        asset_type_id=type_id,
        identifier="Componente",
        parent_asset_id=root["id"],
    )

    other_root = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Outra Raiz"
    )

    assert_problem(
        await client.patch(
            f"/api/v1/assets/{component['id']}",
            headers=auth_headers,
            json={"parent_asset_id": other_root["id"]},
        ),
        400,
        "parent_asset_id e imutavel apos a criacao.",
    )


async def test_assets_update_identifier_and_status(client, auth_headers):
    type_id = await _create_type(client, auth_headers)
    root = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Original"
    )

    updated = (
        await client.patch(
            f"/api/v1/assets/{root['id']}",
            headers=auth_headers,
            json={"identifier": "Renomeado", "status": "retired"},
        )
    ).json()["data"]
    assert updated["identifier"] == "Renomeado"
    assert updated["status"] == "retired"

    # invalid status is rejected by the schema (422)
    bad = await client.patch(
        f"/api/v1/assets/{root['id']}",
        headers=auth_headers,
        json={"status": "banana"},
    )
    assert bad.status_code == 422


async def test_assets_list_by_client(client, auth_headers):
    # CA4: filtering by client_id returns only that client's assets.
    type_id = await _create_type(client, auth_headers)
    client_a = await _create_client(client, auth_headers, name="Cliente A")
    client_b = await _create_client(client, auth_headers, name="Cliente B")

    asset_a = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Ativo A", client_id=client_a
    )
    await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Ativo B", client_id=client_b
    )

    listing = (
        await client.get(f"/api/v1/assets?client_id={client_a}", headers=auth_headers)
    ).json()
    assert [a["id"] for a in listing["data"]] == [asset_a["id"]]
    assert_pagination_meta(
        listing, total=1, page=1, page_size=20, has_next=False, total_pages=1
    )


async def test_assets_archived_type_blocks_creation(client, auth_headers):
    # V8: cannot create an asset referencing an archived type.
    type_id = await _create_type(client, auth_headers)
    await client.delete(f"/api/v1/asset-types/{type_id}", headers=auth_headers)

    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={"asset_type_id": type_id, "identifier": "Com tipo arquivado"},
        ),
        400,
        "Tipo de ativo esta arquivado.",
    )


async def test_assets_inactive_client_rejected(client, auth_headers):
    # V9: cannot reference an inactive client.
    type_id = await _create_type(client, auth_headers)
    client_id = await _create_client(client, auth_headers)
    await client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)

    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "asset_type_id": type_id,
                "identifier": "Com cliente inativo",
                "client_id": client_id,
            },
        ),
        400,
        "Cliente esta inativo.",
    )


async def test_assets_isolated_by_company(client, auth_headers, viewer_headers):
    # CA6: an asset from another company is not visible.
    type_id = await _create_type(client, auth_headers)
    asset = await _create_asset(
        client, auth_headers, asset_type_id=type_id, identifier="Ativo Isolado"
    )

    assert_problem(
        await client.get(f"/api/v1/assets/{asset['id']}", headers=viewer_headers),
        404,
        "Ativo nao encontrado.",
    )


async def test_assets_write_blocked_for_inspector(client, inspector_headers):
    assert_problem(
        await client.post(
            "/api/v1/assets",
            headers=inspector_headers,
            json={
                "asset_type_id": "00000000-0000-0000-0000-000000000000",
                "identifier": "Negada",
            },
        ),
        403,
        "Usuario sem permissao para executar esta acao.",
    )


async def test_assets_requires_auth(client):
    assert_problem(
        await client.get("/api/v1/assets"),
        401,
        "Token de acesso nao informado.",
    )


# --- T5: soft delete em cascata (V6) + reativacao top-down (V7) -----------------


async def _status_of(client, headers, asset_id: str) -> str:
    response = await client.get(f"/api/v1/assets/{asset_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["status"]


async def _build_tree(client, headers) -> tuple[str, str, str]:
    """Raiz -> componente -> neto. Retorna (root_id, component_id, grandchild_id)."""
    type_id = await _create_type(client, headers)
    root = await _create_asset(client, headers, asset_type_id=type_id, identifier="Raiz")
    component = await _create_asset(
        client, headers, asset_type_id=type_id, identifier="Componente",
        parent_asset_id=root["id"],
    )
    grandchild = await _create_asset(
        client, headers, asset_type_id=type_id, identifier="Neto",
        parent_asset_id=component["id"],
    )
    return root["id"], component["id"], grandchild["id"]


async def test_assets_delete_cascades_subtree(client, auth_headers):
    # V6: DELETE numa raiz desativa raiz e toda a subarvore na mesma transacao.
    root_id, component_id, grandchild_id = await _build_tree(client, auth_headers)

    delete = await client.delete(f"/api/v1/assets/{root_id}", headers=auth_headers)
    assert delete.status_code == 200

    # Invariante: nenhum ativo 'active' sob ancestral 'inactive'.
    assert await _status_of(client, auth_headers, root_id) == "inactive"
    assert await _status_of(client, auth_headers, component_id) == "inactive"
    assert await _status_of(client, auth_headers, grandchild_id) == "inactive"

    active = (await client.get("/api/v1/assets?status=active", headers=auth_headers)).json()
    assert active["data"] == []


async def test_assets_delete_audit_records_descendant_count(client, auth_headers):
    # Auditoria asset.deactivated na raiz com contagem de descendentes (2: componente + neto).
    root_id, _, _ = await _build_tree(client, auth_headers)
    await client.delete(f"/api/v1/assets/{root_id}", headers=auth_headers)

    logs = (
        await client.get(
            "/api/v1/audit-logs?action=asset.deactivated", headers=auth_headers
        )
    ).json()
    assert logs["data"], logs
    entry = logs["data"][0]
    assert entry["meta"]["identifier"] == "Raiz"
    assert entry["meta"]["descendants"] == 2


async def test_assets_reactivation_is_top_down(client, auth_headers):
    # V7: reativacao so com pai ativo; reativar nao cascateia para os filhos.
    root_id, component_id, grandchild_id = await _build_tree(client, auth_headers)
    await client.delete(f"/api/v1/assets/{root_id}", headers=auth_headers)

    # Reativar o componente com pai (raiz) inativo -> 400.
    assert_problem(
        await client.patch(
            f"/api/v1/assets/{component_id}",
            headers=auth_headers,
            json={"status": "active"},
        ),
        400,
        "Nao e possivel reativar: o ativo pai esta inativo.",
    )

    # Reativar a raiz (sem pai) -> ok; nao cascateia para o componente.
    reactivated = await client.patch(
        f"/api/v1/assets/{root_id}", headers=auth_headers, json={"status": "active"}
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["data"]["status"] == "active"
    assert await _status_of(client, auth_headers, component_id) == "inactive"

    # Com a raiz ativa, reativar o componente -> ok; nao cascateia para o neto.
    component_reactivated = await client.patch(
        f"/api/v1/assets/{component_id}", headers=auth_headers, json={"status": "active"}
    )
    assert component_reactivated.status_code == 200
    assert await _status_of(client, auth_headers, grandchild_id) == "inactive"
