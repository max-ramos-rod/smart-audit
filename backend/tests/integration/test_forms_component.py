"""DR-0002 Fases 2-4 / T2 — escopo de componente (component_type_id) na versão do formulário."""
from backend.tests.integration.test_auth import assert_problem


async def _login(client, user) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert res.status_code == 200
    return res.json()["data"]["access_token"]


def _headers(token: str, company_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Company-Id": company_id}


async def _create_asset_type(client, headers, name: str = "Roda") -> str:
    res = await client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


def _scoped_field(component_type_id: str | None, field_type: str = "boolean") -> dict:
    field: dict = {
        "key": "pressao_pneu",
        "label": "Pressao do pneu",
        "field_type": field_type,
        "required": True,
        "position": 1,
        "config_json": {},
    }
    if component_type_id is not None:
        field["component_type_id"] = component_type_id
    return field


async def test_create_form_with_valid_component_type(client, auth_headers):
    type_id = await _create_asset_type(client, auth_headers)
    res = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={"name": "Form Escopado", "fields": [_scoped_field(type_id)]},
    )
    assert res.status_code == 200, res.text
    field = res.json()["data"]["current_version"]["fields"][0]
    assert field["component_type_id"] == type_id


async def test_publish_version_with_valid_component_type(client, auth_headers):
    type_id = await _create_asset_type(client, auth_headers)
    form_id = (
        await client.post(
            "/api/v1/forms",
            headers=auth_headers,
            json={"name": "Form", "fields": [_scoped_field(None)]},
        )
    ).json()["data"]["id"]

    res = await client.post(
        f"/api/v1/forms/{form_id}/versions",
        headers=auth_headers,
        json={"fields": [_scoped_field(type_id)]},
    )
    assert res.status_code == 200, res.text
    field = res.json()["data"]["current_version"]["fields"][0]
    assert field["component_type_id"] == type_id


async def test_field_without_component_type_is_unchanged(client, auth_headers):
    # Retrocompat: campo geral mantém component_type_id None.
    res = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={"name": "Form Geral", "fields": [_scoped_field(None)]},
    )
    assert res.status_code == 200
    assert res.json()["data"]["current_version"]["fields"][0]["component_type_id"] is None


async def test_foreign_company_component_type_rejected(client, multi_company_user):
    token = await _login(client, multi_company_user)
    headers_a = _headers(token, multi_company_user["company_a_id"])
    headers_b = _headers(token, multi_company_user["company_b_id"])

    foreign_type = await _create_asset_type(client, headers_b, "Tipo Empresa B")
    assert_problem(
        await client.post(
            "/api/v1/forms",
            headers=headers_a,
            json={"name": "Form", "fields": [_scoped_field(foreign_type)]},
        ),
        400,
        "Tipo de componente invalido.",
    )


async def test_nonexistent_component_type_rejected(client, auth_headers):
    assert_problem(
        await client.post(
            "/api/v1/forms",
            headers=auth_headers,
            json={
                "name": "Form",
                "fields": [_scoped_field("00000000-0000-0000-0000-000000000000")],
            },
        ),
        400,
        "Tipo de componente invalido.",
    )


async def test_section_with_component_type_rejected(client, auth_headers):
    type_id = await _create_asset_type(client, auth_headers)
    field = _scoped_field(type_id, field_type="section")
    field["key"] = "__section_1__"
    assert_problem(
        await client.post(
            "/api/v1/forms",
            headers=auth_headers,
            json={"name": "Form", "fields": [field]},
        ),
        400,
        "Campo do tipo section nao pode ter escopo de componente.",
    )
