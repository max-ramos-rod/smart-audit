"""Filtro ?client_id= em GET /submissions (PR-6).

Inspeções são associadas a um cliente através do ativo vinculado
(submissions.asset_id -> assets.client_id). O filtro faz join em assets, de modo
que inspeções sem ativo (asset_id NULL) ou cujo ativo pertence a outro cliente
não aparecem. O escopo de empresa (tenant) continua sendo respeitado.
"""


async def _login(client, user) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _headers(token: str, company_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Company-Id": company_id}


async def _create_form(client, headers) -> str:
    res = await client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": "Form Filtro Cliente",
            "description": "",
            "fields": [
                {
                    "key": "item_ok",
                    "label": "Item OK",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
            ],
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_type(client, headers, name: str = "Veiculo") -> str:
    res = await client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_client(client, headers, name: str) -> str:
    res = await client.post("/api/v1/clients", headers=headers, json={"name": name})
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_asset(
    client, headers, type_id: str, identifier: str, client_id: str | None = None
) -> str:
    body: dict[str, object] = {"asset_type_id": type_id, "identifier": identifier}
    if client_id is not None:
        body["client_id"] = client_id
    res = await client.post("/api/v1/assets", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _create_submission(client, headers, form_id: str, asset_id: str | None = None) -> str:
    body: dict[str, object] = {"form_id": form_id}
    if asset_id is not None:
        body["asset_id"] = asset_id
    res = await client.post("/api/v1/submissions", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def test_list_submissions_filtered_by_client(client, auth_headers):
    """Retorna apenas inspeções cujo ativo pertence ao cliente informado."""
    form_id = await _create_form(client, auth_headers)
    type_id = await _create_type(client, auth_headers)

    client_a = await _create_client(client, auth_headers, "Cliente A")
    client_b = await _create_client(client, auth_headers, "Cliente B")

    asset_a = await _create_asset(client, auth_headers, type_id, "Ativo A", client_a)
    asset_b = await _create_asset(client, auth_headers, type_id, "Ativo B", client_b)
    asset_orphan = await _create_asset(client, auth_headers, type_id, "Ativo sem cliente")

    sub_a = await _create_submission(client, auth_headers, form_id, asset_a)
    sub_b = await _create_submission(client, auth_headers, form_id, asset_b)
    sub_orphan = await _create_submission(client, auth_headers, form_id, asset_orphan)
    sub_no_asset = await _create_submission(client, auth_headers, form_id)

    listing = (
        await client.get(f"/api/v1/submissions?client_id={client_a}", headers=auth_headers)
    ).json()
    ids = {i["id"] for i in listing["data"]}

    assert ids == {sub_a}
    # Excluídos: outro cliente, ativo sem cliente e inspeção sem ativo.
    assert sub_b not in ids
    assert sub_orphan not in ids
    assert sub_no_asset not in ids


async def test_list_submissions_by_client_empty_when_no_assets(client, auth_headers):
    """Cliente sem ativos/inspeções retorna lista vazia (sem erro)."""
    form_id = await _create_form(client, auth_headers)
    await _create_submission(client, auth_headers, form_id)  # inspeção sem ativo

    empty_client = await _create_client(client, auth_headers, "Cliente Vazio")
    listing = (
        await client.get(f"/api/v1/submissions?client_id={empty_client}", headers=auth_headers)
    ).json()
    assert listing["data"] == []


async def test_list_submissions_by_client_respects_tenant(client, multi_company_user):
    """client_id de uma empresa não vaza inspeções para outra empresa do mesmo usuário."""
    token = await _login(client, multi_company_user)
    headers_a = _headers(token, multi_company_user["company_a_id"])
    headers_b = _headers(token, multi_company_user["company_b_id"])

    form_a = await _create_form(client, headers_a)
    type_a = await _create_type(client, headers_a)
    client_a = await _create_client(client, headers_a, "Cliente Empresa A")
    asset_a = await _create_asset(client, headers_a, type_a, "Ativo Empresa A", client_a)
    await _create_submission(client, headers_a, form_a, asset_a)

    # Visto da empresa A: aparece.
    seen_a = (
        await client.get(f"/api/v1/submissions?client_id={client_a}", headers=headers_a)
    ).json()
    assert len(seen_a["data"]) == 1

    # Visto da empresa B com o mesmo client_id: nada (escopo de empresa).
    seen_b = (
        await client.get(f"/api/v1/submissions?client_id={client_a}", headers=headers_b)
    ).json()
    assert seen_b["data"] == []
