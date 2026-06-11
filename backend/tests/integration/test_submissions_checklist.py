"""DR-0002 Fases 2-4 / T3 — motor de expansão do checklist por componente."""


async def _create_type(client, headers, name: str) -> str:
    res = await client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_asset(
    client, headers, type_id: str, identifier: str, parent: str | None = None
) -> str:
    body: dict = {"asset_type_id": type_id, "identifier": identifier}
    if parent is not None:
        body["parent_asset_id"] = parent
    res = await client.post("/api/v1/assets", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_form(client, headers, fields: list[dict]) -> str:
    res = await client.post(
        "/api/v1/forms", headers=headers, json={"name": "Form Componente", "fields": fields}
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_submission(client, headers, form_id: str, asset_id: str | None = None) -> dict:
    body: dict = {"form_id": form_id}
    if asset_id is not None:
        body["asset_id"] = asset_id
    res = await client.post("/api/v1/submissions", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _general_field() -> dict:
    return {
        "key": "obs_geral",
        "label": "Observacao geral",
        "field_type": "text",
        "required": False,
        "position": 1,
        "config_json": {},
    }


def _scoped_field(type_id: str) -> dict:
    return {
        "key": "pressao_pneu",
        "label": "Pressao do pneu",
        "field_type": "boolean",
        "required": True,
        "position": 2,
        "config_json": {},
        "component_type_id": type_id,
    }


async def test_scoped_field_expands_per_component(client, auth_headers):
    veiculo = await _create_type(client, auth_headers, "Veiculo")
    roda = await _create_type(client, auth_headers, "Roda")
    root = await _create_asset(client, auth_headers, veiculo, "Caminhao ABC")
    for pos in ("DD", "DE", "TD", "TE"):
        await _create_asset(client, auth_headers, roda, f"Roda {pos}", parent=root)

    form_id = await _create_form(client, auth_headers, [_general_field(), _scoped_field(roda)])
    submission = await _create_submission(client, auth_headers, form_id, asset_id=root)

    checklist = {item["field_key"]: item for item in submission["checklist"]}
    assert submission["warnings"] == []

    # Campo geral: uma instância, sem componentes.
    assert checklist["obs_geral"]["components"] == []
    assert checklist["obs_geral"]["component_type_id"] is None

    # Campo escopado: 4 instâncias (uma por roda), com label/type/path.
    scoped = checklist["pressao_pneu"]
    assert scoped["component_type_id"] == roda
    assert len(scoped["components"]) == 4
    labels = {c["label"] for c in scoped["components"]}
    assert labels == {"Roda DD", "Roda DE", "Roda TD", "Roda TE"}
    first = scoped["components"][0]
    assert first["type"] == "Roda"
    assert first["path"].startswith("Caminhao ABC > Roda ")
    assert first["asset_id"]


async def test_scoped_field_without_matching_components_is_omitted_with_warning(
    client, auth_headers
):
    veiculo = await _create_type(client, auth_headers, "Veiculo")
    roda = await _create_type(client, auth_headers, "Roda")
    # Ativo sem nenhum componente do tipo Roda.
    root = await _create_asset(client, auth_headers, veiculo, "Carro Sem Rodas")

    form_id = await _create_form(client, auth_headers, [_general_field(), _scoped_field(roda)])
    submission = await _create_submission(client, auth_headers, form_id, asset_id=root)

    keys = {item["field_key"] for item in submission["checklist"]}
    assert keys == {"obs_geral"}  # campo escopado omitido
    assert any("pressao_pneu" in w for w in submission["warnings"])


async def test_scoped_field_without_asset_warns_and_omits(client, auth_headers):
    roda = await _create_type(client, auth_headers, "Roda")
    form_id = await _create_form(client, auth_headers, [_general_field(), _scoped_field(roda)])
    # Inspeção sem ativo vinculado.
    submission = await _create_submission(client, auth_headers, form_id)

    keys = {item["field_key"] for item in submission["checklist"]}
    assert keys == {"obs_geral"}
    assert any("ativo vinculado" in w for w in submission["warnings"])


async def test_general_only_form_has_no_warnings(client, auth_headers):
    # Retrocompat: formulário sem campo escopado não gera avisos nem expansão.
    form_id = await _create_form(client, auth_headers, [_general_field()])
    submission = await _create_submission(client, auth_headers, form_id)
    assert submission["warnings"] == []
    assert [i["field_key"] for i in submission["checklist"]] == ["obs_geral"]
    assert submission["checklist"][0]["components"] == []
