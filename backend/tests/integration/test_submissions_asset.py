from backend.tests.integration.test_auth import assert_problem


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
            "name": "Form Vinculo Ativo",
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


async def _create_asset(client, headers, identifier: str = "Caminhao 01") -> str:
    type_res = await client.post(
        "/api/v1/asset-types", headers=headers, json={"name": "Veiculo"}
    )
    assert type_res.status_code == 200, type_res.text
    type_id = type_res.json()["data"]["id"]
    asset_res = await client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_type_id": type_id, "identifier": identifier},
    )
    assert asset_res.status_code == 200, asset_res.text
    return asset_res.json()["data"]["id"]


async def test_create_submission_without_asset_is_unchanged(client, auth_headers):
    # Retrocompatibilidade: sem asset_id, comportamento idêntico ao atual.
    form_id = await _create_form(client, auth_headers)
    res = await client.post(
        "/api/v1/submissions", headers=auth_headers, json={"form_id": form_id}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["asset_id"] is None
    assert data["asset_identifier"] is None


async def test_create_submission_with_asset_links_it(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    asset_id = await _create_asset(client, auth_headers, "Caminhao 99")

    res = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id, "asset_id": asset_id},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["asset_id"] == asset_id
    assert data["asset_identifier"] == "Caminhao 99"

    submission_id = data["id"]
    # Detalhe traz o vínculo.
    detail = (await client.get(f"/api/v1/submissions/{submission_id}", headers=auth_headers)).json()
    assert detail["data"]["asset_id"] == asset_id
    assert detail["data"]["asset_identifier"] == "Caminhao 99"

    # Item de lista traz o vínculo.
    listing = (await client.get("/api/v1/submissions", headers=auth_headers)).json()
    item = next(i for i in listing["data"] if i["id"] == submission_id)
    assert item["asset_id"] == asset_id
    assert item["asset_identifier"] == "Caminhao 99"


async def test_create_submission_with_foreign_asset_rejected(client, multi_company_user):
    # V1: asset_id de outra empresa é rejeitado.
    token = await _login(client, multi_company_user)
    headers_a = _headers(token, multi_company_user["company_a_id"])
    headers_b = _headers(token, multi_company_user["company_b_id"])

    form_id = await _create_form(client, headers_a)
    foreign_asset = await _create_asset(client, headers_b, "Ativo da Empresa B")

    assert_problem(
        await client.post(
            "/api/v1/submissions",
            headers=headers_a,
            json={"form_id": form_id, "asset_id": foreign_asset},
        ),
        400,
        "Ativo invalido.",
    )


async def test_create_submission_with_inactive_asset_rejected(client, auth_headers):
    # V2: não se inicia inspeção sobre ativo desativado.
    form_id = await _create_form(client, auth_headers)
    asset_id = await _create_asset(client, auth_headers, "Ativo Inativo")
    await client.delete(f"/api/v1/assets/{asset_id}", headers=auth_headers)

    assert_problem(
        await client.post(
            "/api/v1/submissions",
            headers=auth_headers,
            json={"form_id": form_id, "asset_id": asset_id},
        ),
        400,
        "Ativo nao esta ativo.",
    )


async def test_list_submissions_filtered_by_asset(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    asset_a = await _create_asset(client, auth_headers, "Ativo A")
    asset_b = await _create_asset(client, auth_headers, "Ativo B")

    res_a = await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id, "asset_id": asset_a},
    )
    submission_a = res_a.json()["data"]["id"]
    await client.post(
        "/api/v1/submissions",
        headers=auth_headers,
        json={"form_id": form_id, "asset_id": asset_b},
    )

    listing = (
        await client.get(f"/api/v1/submissions?asset_id={asset_a}", headers=auth_headers)
    ).json()
    assert [i["id"] for i in listing["data"]] == [submission_a]
