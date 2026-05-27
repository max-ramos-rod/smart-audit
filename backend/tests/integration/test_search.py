from backend.tests.integration.test_auth import assert_problem

_FORM_PAYLOAD = {
    "name": "Checklist NR-10",
    "fields": [
        {
            "key": "ok",
            "label": "OK",
            "field_type": "boolean",
            "required": True,
            "position": 1,
            "config_json": {},
        }
    ],
}


async def _create_form(client, headers):
    resp = await client.post("/api/v1/forms", headers=headers, json=_FORM_PAYLOAD)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


async def test_search_returns_matching_forms(client, auth_headers):
    await _create_form(client, auth_headers)
    response = await client.get("/api/v1/search?q=NR-10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["forms"]) == 1
    assert data["forms"][0]["name"] == "Checklist NR-10"
    assert data["submissions"] == []


async def test_search_returns_matching_submissions(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    await client.post("/api/v1/submissions", headers=auth_headers, json={"form_id": form_id})

    response = await client.get("/api/v1/search?q=NR-10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["forms"]) == 1
    assert len(data["submissions"]) == 1
    assert data["submissions"][0]["form_name"] == "Checklist NR-10"


async def test_search_response_shape(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    await client.post("/api/v1/submissions", headers=auth_headers, json={"form_id": form_id})

    response = await client.get("/api/v1/search?q=NR-10", headers=auth_headers)
    data = response.json()["data"]

    form = data["forms"][0]
    assert "id" in form
    assert "name" in form
    assert "is_active" in form
    assert "current_version_number" in form

    sub = data["submissions"][0]
    assert "id" in sub
    assert "form_name" in sub
    assert "status" in sub
    assert "score" in sub
    assert "started_at" in sub


async def test_search_no_results_for_unmatched_query(client, auth_headers):
    response = await client.get("/api/v1/search?q=xyz-nao-existe", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["forms"] == []
    assert data["submissions"] == []


async def test_search_is_case_insensitive(client, auth_headers):
    await _create_form(client, auth_headers)
    response = await client.get("/api/v1/search?q=nr-10", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]["forms"]) == 1


async def test_search_partial_match(client, auth_headers):
    await _create_form(client, auth_headers)
    response = await client.get("/api/v1/search?q=Checklist", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]["forms"]) == 1


async def test_search_respects_company_isolation(client, auth_headers, inspector_headers):
    await _create_form(client, auth_headers)
    response = await client.get("/api/v1/search?q=NR-10", headers=inspector_headers)
    assert response.status_code == 200
    assert response.json()["data"]["forms"] == []


async def test_search_requires_auth(client):
    response = await client.get("/api/v1/search?q=test")
    assert_problem(response, 401, "Token de acesso nao informado.")


async def test_search_rejects_short_query(client, auth_headers):
    response = await client.get("/api/v1/search?q=a", headers=auth_headers)
    assert response.status_code == 422
