
from backend.tests.integration.test_auth import assert_pagination_meta, assert_problem


async def test_forms_create_list_and_publish_version(client, auth_headers):
    create_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Teste",
            "description": "Fluxo de teste",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "temperatura",
                    "label": "Temperatura",
                    "field_type": "number",
                    "required": True,
                    "position": 2,
                    "config_json": {"min": -30, "max": 20},
                },
            ],
        },
    )

    assert create_response.status_code == 200
    form_payload = create_response.json()["data"]
    assert form_payload["name"] == "Checklist Teste"
    assert form_payload["current_version"]["version"] == 1
    form_id = form_payload["id"]

    list_response = await client.get("/api/v1/forms?page=1&page_size=10", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["data"]) == 1
    assert_pagination_meta(
        list_payload,
        total=1,
        page=1,
        page_size=10,
        has_next=False,
        total_pages=1,
    )

    publish_response = await client.post(
        f"/api/v1/forms/{form_id}/versions",
        headers=auth_headers,
        json={
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor presente",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "temperatura",
                    "label": "Temperatura",
                    "field_type": "number",
                    "required": True,
                    "position": 2,
                    "config_json": {"min": -30, "max": 20},
                },
                {
                    "key": "limpeza",
                    "label": "Limpeza",
                    "field_type": "boolean",
                    "required": False,
                    "position": 3,
                    "config_json": {},
                },
            ]
        },
    )

    assert publish_response.status_code == 200
    published_payload = publish_response.json()["data"]
    assert published_payload["current_version"]["version"] == 2
    assert len(published_payload["current_version"]["fields"]) == 3


async def test_forms_list_supports_pagination(client, auth_headers):
    for index in range(3):
        response = await client.post(
            "/api/v1/forms",
            headers=auth_headers,
            json={
                "name": f"Checklist {index}",
                "description": "Paginacao",
                "fields": [
                    {
                        "key": f"campo_{index}",
                        "label": f"Campo {index}",
                        "field_type": "boolean",
                        "required": True,
                        "position": 1,
                        "config_json": {},
                    }
                ],
            },
        )
        assert response.status_code == 200

    response = await client.get("/api/v1/forms?page=2&page_size=2", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert_pagination_meta(
        payload,
        total=3,
        page=2,
        page_size=2,
        has_next=False,
        total_pages=2,
    )


async def test_forms_reject_duplicate_field_keys(client, auth_headers):
    response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Invalido",
            "description": "Campos duplicados",
            "fields": [
                {
                    "key": "extintor",
                    "label": "Extintor 1",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "extintor",
                    "label": "Extintor 2",
                    "field_type": "boolean",
                    "required": False,
                    "position": 2,
                    "config_json": {},
                },
            ],
        },
    )

    assert_problem(response, 400, "As chaves dos campos devem ser unicas.")


async def test_forms_reject_duplicate_positions(client, auth_headers):
    response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Checklist Invalido",
            "description": "Posicoes duplicadas",
            "fields": [
                {
                    "key": "campo_1",
                    "label": "Campo 1",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "campo_2",
                    "label": "Campo 2",
                    "field_type": "boolean",
                    "required": False,
                    "position": 1,
                    "config_json": {},
                },
            ],
        },
    )

    assert_problem(response, 400, "As posicoes dos campos devem ser unicas.")


_MINIMAL_FIELD = {
    "key": "campo",
    "label": "Campo",
    "field_type": "boolean",
    "required": True,
    "position": 1,
    "config_json": {},
}


async def test_get_form_version_returns_exact_version(client, auth_headers):
    create_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Form Versoes",
            "fields": [_MINIMAL_FIELD],
        },
    )
    form_id = create_response.json()["data"]["id"]
    v1_id = create_response.json()["data"]["current_version"]["id"]

    await client.post(
        f"/api/v1/forms/{form_id}/versions",
        headers=auth_headers,
        json={
            "fields": [
                _MINIMAL_FIELD,
                {
                    "key": "extra",
                    "label": "Extra",
                    "field_type": "text",
                    "required": False,
                    "position": 2,
                    "config_json": {},
                },
            ]
        },
    )

    response = await client.get(f"/api/v1/forms/{form_id}/versions/{v1_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"] == 1
    assert len(data["fields"]) == 1


async def test_get_form_version_404_for_nonexistent(client, auth_headers):
    create_response = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={"name": "Form 404", "fields": [_MINIMAL_FIELD]},
    )
    form_id = create_response.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/forms/{form_id}/versions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert_problem(response, 404, "Versao nao encontrada.")


async def test_forms_create_blocked_for_inspector(client, inspector_headers):
    response = await client.post(
        "/api/v1/forms",
        headers=inspector_headers,
        json={"name": "Blocked", "fields": [_MINIMAL_FIELD]},
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_forms_publish_version_blocked_for_inspector(client, inspector_headers):
    response = await client.post(
        "/api/v1/forms/00000000-0000-0000-0000-000000000000/versions",
        headers=inspector_headers,
        json={"fields": [_MINIMAL_FIELD]},
    )
    assert_problem(response, 403, "Usuario sem permissao para executar esta acao.")


async def test_list_form_versions(client, auth_headers):
    """GET /forms/{id}/versions retorna lista de versões com fields_count."""
    # Criar formulário
    create_res = await client.post(
        "/api/v1/forms",
        headers=auth_headers,
        json={
            "name": "Formulário para teste de versões",
            "fields": [
                {
                    "key": "campo_v1",
                    "label": "Campo v1",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                }
            ],
        },
    )
    assert create_res.status_code == 200
    form_id = create_res.json()["data"]["id"]

    # Publicar nova versão
    await client.post(
        f"/api/v1/forms/{form_id}/versions",
        headers=auth_headers,
        json={
            "fields": [
                {
                    "key": "campo_v2_a",
                    "label": "Campo v2 A",
                    "field_type": "boolean",
                    "required": True,
                    "position": 1,
                    "config_json": {},
                },
                {
                    "key": "campo_v2_b",
                    "label": "Campo v2 B",
                    "field_type": "text",
                    "required": False,
                    "position": 2,
                    "config_json": {},
                },
            ],
        },
    )

    # Listar versões
    res = await client.get(f"/api/v1/forms/{form_id}/versions", headers=auth_headers)
    assert res.status_code == 200
    versions = res.json()["data"]

    assert len(versions) == 2
    # Ordenadas por versão decrescente
    assert versions[0]["version"] > versions[1]["version"]
    # Campos corretos
    for v in versions:
        assert "id" in v
        assert "version" in v
        assert "status" in v
        assert "published_at" in v
        assert "fields_count" in v
        assert isinstance(v["fields_count"], int)
        assert v["fields_count"] > 0
