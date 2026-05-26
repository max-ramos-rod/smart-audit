from backend.tests.integration.test_auth import assert_problem


_FORM_PAYLOAD = {
    "name": "Stats Form",
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


async def _create_submission(client, headers, form_id):
    resp = await client.post("/api/v1/submissions", headers=headers, json={"form_id": form_id})
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


async def _finish_submission(client, headers, submission_id):
    await client.put(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=headers,
        json={"answers": [{"field_key": "ok", "value": True}]},
    )
    resp = await client.post(f"/api/v1/submissions/{submission_id}/finish", headers=headers)
    assert resp.status_code == 200


async def test_me_stats_empty(client, auth_headers):
    response = await client.get("/api/v1/me/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_submissions"] == 0
    assert data["completed"] == 0
    assert data["in_progress"] == 0
    assert data["avg_score"] is None
    assert data["recent"] == []


async def test_me_stats_counts_completed_and_in_progress(client, auth_headers):
    form_id = await _create_form(client, auth_headers)

    sub1_id = await _create_submission(client, auth_headers, form_id)
    await _finish_submission(client, auth_headers, sub1_id)

    await _create_submission(client, auth_headers, form_id)

    response = await client.get("/api/v1/me/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_submissions"] == 2
    assert data["completed"] == 1
    assert data["in_progress"] == 1
    assert data["avg_score"] == 100.0


async def test_me_stats_recent_includes_all_submissions(client, auth_headers):
    form_id = await _create_form(client, auth_headers)

    sub1_id = await _create_submission(client, auth_headers, form_id)
    sub2_id = await _create_submission(client, auth_headers, form_id)

    response = await client.get("/api/v1/me/stats", headers=auth_headers)
    data = response.json()["data"]
    recent_ids = {item["id"] for item in data["recent"]}
    assert len(recent_ids) == 2
    assert sub1_id in recent_ids
    assert sub2_id in recent_ids


async def test_me_stats_respects_company_isolation(client, auth_headers, inspector_headers):
    form_id = await _create_form(client, auth_headers)
    await _create_submission(client, auth_headers, form_id)

    response = await client.get("/api/v1/me/stats", headers=inspector_headers)
    data = response.json()["data"]
    assert data["total_submissions"] == 0


async def test_me_stats_requires_auth(client):
    response = await client.get("/api/v1/me/stats")
    assert_problem(response, 401, "Token de acesso nao informado.")
