"""Integration tests for GET /submissions/export (CSV)."""
from backend.tests.integration.test_auth import assert_problem

_FORM_PAYLOAD = {
    "name": "Checklist Export",
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
    await client.put(
        f"/api/v1/submissions/{submission_id}/conformity",
        headers=headers,
        json={"items": [{"field_key": "ok", "status": "conforme", "justification": None}]},
    )
    resp = await client.post(f"/api/v1/submissions/{submission_id}/finish", headers=headers)
    assert resp.status_code == 200


async def test_export_returns_csv_content_type(client, auth_headers):
    response = await client.get("/api/v1/submissions/export", headers=auth_headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


async def test_export_empty_returns_only_headers(client, auth_headers):
    response = await client.get("/api/v1/submissions/export", headers=auth_headers)
    lines = response.text.lstrip("﻿").strip().splitlines()
    assert len(lines) == 1
    assert lines[0] == "id,formulario,status,score,iniciada_em,finalizada_em"


async def test_export_contains_submission_data(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _finish_submission(client, auth_headers, sub_id)

    response = await client.get("/api/v1/submissions/export", headers=auth_headers)
    body = response.text.lstrip("﻿")
    assert sub_id in body
    assert "Checklist Export" in body
    assert "completed" in body
    assert "100.00" in body


async def test_export_in_progress_submission(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    sub_id = await _create_submission(client, auth_headers, form_id)

    response = await client.get("/api/v1/submissions/export", headers=auth_headers)
    body = response.text.lstrip("﻿")
    assert sub_id in body
    assert "in_progress" in body


async def test_export_filter_by_status(client, auth_headers):
    form_id = await _create_form(client, auth_headers)
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _finish_submission(client, auth_headers, sub_id)
    in_progress_id = await _create_submission(client, auth_headers, form_id)

    completed_resp = await client.get(
        "/api/v1/submissions/export?status=completed", headers=auth_headers
    )
    body = completed_resp.text.lstrip("﻿")
    assert sub_id in body
    assert in_progress_id not in body

    in_progress_resp = await client.get(
        "/api/v1/submissions/export?status=in_progress", headers=auth_headers
    )
    body2 = in_progress_resp.text.lstrip("﻿")
    assert in_progress_id in body2
    assert sub_id not in body2


async def test_export_respects_company_isolation(client, auth_headers, inspector_headers):
    form_id = await _create_form(client, auth_headers)
    await _create_submission(client, auth_headers, form_id)

    response = await client.get("/api/v1/submissions/export", headers=inspector_headers)
    lines = response.text.lstrip("﻿").strip().splitlines()
    assert len(lines) == 1  # only header row


async def test_export_requires_auth(client):
    response = await client.get("/api/v1/submissions/export")
    assert_problem(response, 401, "Token de acesso nao informado.")
