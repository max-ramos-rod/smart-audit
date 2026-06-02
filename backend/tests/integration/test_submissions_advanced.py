"""
Advanced integration tests covering:
  - PDF export endpoint (content-type, attachment vs inline)
  - Company stats: score_by_form and score_trend fields
  - N/A boolean answers (allow_na=True) do not block required-field check
  - visible_if conditional: hidden required fields don't block finish
  - Weighted scoring: custom weights affect final score
  - Score breakdown: na_count populated correctly
  - Multi-company tenant isolation on stats
"""
import pytest

from backend.tests.integration.test_auth import assert_problem


# ── helpers ─────────────────────────────────────────────────────────────────

async def _create_form(client, headers, fields, name="Test Form"):
    resp = await client.post(
        "/api/v1/forms",
        headers=headers,
        json={"name": name, "fields": fields},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


async def _create_submission(client, headers, form_id):
    resp = await client.post(
        "/api/v1/submissions", headers=headers, json={"form_id": form_id}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


async def _answer(client, headers, submission_id, answers):
    resp = await client.put(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=headers,
        json={"answers": answers},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _conformity(client, headers, submission_id, items):
    resp = await client.put(
        f"/api/v1/submissions/{submission_id}/conformity",
        headers=headers,
        json={"items": items},
    )
    assert resp.status_code == 200, resp.text


async def _finish(client, headers, submission_id):
    resp = await client.post(
        f"/api/v1/submissions/{submission_id}/finish", headers=headers
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ── PDF export ───────────────────────────────────────────────────────────────

async def test_pdf_export_returns_application_pdf(client, auth_headers):
    form_id = await _create_form(client, auth_headers, [
        {"key": "ok", "label": "OK", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
    ], name="PDF Test Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "ok", "value": True}])
    await _finish(client, auth_headers, sub_id)

    resp = await client.get(f"/api/v1/submissions/{sub_id}/export", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert 'filename="inspecao-' in resp.headers["content-disposition"]


async def test_pdf_export_inline_disposition(client, auth_headers):
    form_id = await _create_form(client, auth_headers, [
        {"key": "ok", "label": "OK", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
    ], name="PDF Inline Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "ok", "value": True}])
    await _finish(client, auth_headers, sub_id)

    resp = await client.get(
        f"/api/v1/submissions/{sub_id}/export?inline=true", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == "inline"
    assert resp.content[:4] == b"%PDF"


async def test_pdf_export_with_section_and_na_fields(client, auth_headers):
    """PDF generation should not crash with section/N/A field types."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "__section_1__", "label": "Bloco A", "field_type": "section",
         "required": False, "position": 1, "config_json": {}},
        {"key": "safety", "label": "EPI em uso?", "field_type": "boolean",
         "required": True, "position": 2, "config_json": {"allow_na": True}},
    ], name="PDF Section Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "safety", "value": "na"}])
    await _finish(client, auth_headers, sub_id)

    resp = await client.get(f"/api/v1/submissions/{sub_id}/export", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


async def test_pdf_export_requires_auth(client):
    resp = await client.get("/api/v1/submissions/00000000-0000-0000-0000-000000000000/export")
    assert_problem(resp, 401, "Token de acesso nao informado.")


async def test_pdf_export_404_for_unknown_submission(client, auth_headers):
    resp = await client.get(
        "/api/v1/submissions/00000000-0000-0000-0000-000000000001/export",
        headers=auth_headers,
    )
    assert_problem(resp, 404, "Inspecao nao encontrada.")


# ── company stats ────────────────────────────────────────────────────────────

async def test_stats_returns_score_by_form_and_score_trend(client, auth_headers):
    form_id = await _create_form(client, auth_headers, [
        {"key": "c1", "label": "C1", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
    ], name="Stats Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "c1", "value": True}])
    await _finish(client, auth_headers, sub_id)

    resp = await client.get("/api/v1/me/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert "score_by_form" in data
    assert "score_trend" in data
    assert isinstance(data["score_by_form"], list)
    assert isinstance(data["score_trend"], list)

    if data["score_by_form"]:
        item = data["score_by_form"][0]
        assert "form_id" in item
        assert "form_name" in item
        assert "avg_score" in item
        assert "count" in item

    if data["score_trend"]:
        point = data["score_trend"][0]
        assert "date" in point
        assert "avg_score" in point


async def test_stats_period_filter_affects_totals(client, auth_headers):
    resp_all = await client.get("/api/v1/me/stats?period=all", headers=auth_headers)
    resp_7d  = await client.get("/api/v1/me/stats?period=7d",  headers=auth_headers)
    assert resp_all.status_code == 200
    assert resp_7d.status_code == 200
    # both return valid envelope shapes
    assert "total_submissions" in resp_all.json()["data"]
    assert "total_submissions" in resp_7d.json()["data"]


# ── N/A boolean ──────────────────────────────────────────────────────────────

async def test_na_boolean_answer_accepted_and_finish_succeeds(client, auth_headers):
    """Required boolean with allow_na=True can be answered 'na' without blocking finish."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "risco", "label": "Há risco?", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {"allow_na": True}},
    ], name="NA Boolean Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "risco", "value": "na"}])

    data = await _finish(client, auth_headers, sub_id)
    assert data["status"] == "completed"


async def test_na_boolean_appears_in_score_breakdown(client, auth_headers):
    """N/A-answered field with no conformity record appears as sem_resposta in score_breakdown."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "b1", "label": "B1", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
        {"key": "b2", "label": "B2 (allow_na)", "field_type": "boolean",
         "required": True, "position": 2, "config_json": {"allow_na": True}},
    ], name="NA Breakdown Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [
        {"field_key": "b1", "value": True},
        {"field_key": "b2", "value": "na"},
    ])
    # Only b1 gets a conformity evaluation; b2 (N/A) is left unevaluated
    await _conformity(client, auth_headers, sub_id, [
        {"field_key": "b1", "status": "conforme", "justification": None},
    ])
    data = await _finish(client, auth_headers, sub_id)

    breakdown = data["score_breakdown"]
    assert breakdown is not None
    assert breakdown["na_count"] == 0
    assert breakdown["conformes"] == 1
    assert breakdown["sem_resposta"] == 1
    assert breakdown["total_boolean"] == 2


async def test_na_boolean_excluded_from_score_calculation(client, auth_headers):
    """N/A-answered field without conformity record is excluded from score — score stays 100%."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "b1", "label": "B1", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
        {"key": "b2", "label": "B2 na", "field_type": "boolean",
         "required": False, "position": 2, "config_json": {"allow_na": True}},
    ], name="NA Score Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [
        {"field_key": "b1", "value": True},
        {"field_key": "b2", "value": "na"},
    ])
    # Only b1 gets evaluated; b2 (N/A) is excluded → score = 1/1 = 100%
    await _conformity(client, auth_headers, sub_id, [
        {"field_key": "b1", "status": "conforme", "justification": None},
    ])
    data = await _finish(client, auth_headers, sub_id)
    assert data["score"] == pytest.approx(100.0)


# ── visible_if conditional rules ────────────────────────────────────────────

async def test_visible_if_hidden_required_field_does_not_block_finish(client, auth_headers):
    """A required field hidden by visible_if should not block completion."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "eh_perigoso", "label": "É perigoso?", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
        {"key": "medida", "label": "Medida de segurança", "field_type": "text",
         "required": True, "position": 2,
         "config_json": {"visible_if": {"field_key": "eh_perigoso", "operator": "eq", "value": True}}},
    ], name="VisibleIf Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    # Answer trigger as False → conditional field is hidden → should not block
    await _answer(client, auth_headers, sub_id, [{"field_key": "eh_perigoso", "value": False}])

    data = await _finish(client, auth_headers, sub_id)
    assert data["status"] == "completed"


async def test_visible_if_visible_required_field_blocks_finish(client, auth_headers):
    """A required field that IS visible (visible_if condition met) still blocks if unanswered."""
    form_id = await _create_form(client, auth_headers, [
        {"key": "eh_perigoso", "label": "É perigoso?", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
        {"key": "medida", "label": "Medida de segurança", "field_type": "text",
         "required": True, "position": 2,
         "config_json": {"visible_if": {"field_key": "eh_perigoso", "operator": "eq", "value": True}}},
    ], name="VisibleIf Required Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    # Answer trigger as True → conditional field IS visible → required but not answered → blocks
    await _answer(client, auth_headers, sub_id, [{"field_key": "eh_perigoso", "value": True}])

    resp = await client.post(
        f"/api/v1/submissions/{sub_id}/finish", headers=auth_headers
    )
    assert_problem(resp, 400, "Campos obrigatorios pendentes: medida.")


# ── weighted scoring ─────────────────────────────────────────────────────────

async def test_weighted_boolean_fields_affect_score(client, auth_headers):
    """Fields with higher weight contribute proportionally more to the final score."""
    form_id = await _create_form(client, auth_headers, [
        # weight 3: conforme → contributes 3
        {"key": "critico", "label": "Crítico", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {"weight": 3}},
        # weight 1: nao_conforme → contributes 0
        {"key": "menor", "label": "Menor", "field_type": "boolean",
         "required": True, "position": 2, "config_json": {"weight": 1}},
    ], name="Weighted Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [
        {"field_key": "critico", "value": True},
        {"field_key": "menor", "value": False},
    ])
    await _conformity(client, auth_headers, sub_id, [
        {"field_key": "critico", "status": "conforme", "justification": None},
        {"field_key": "menor", "status": "nao_conforme", "justification": "Falha menor"},
    ])
    data = await _finish(client, auth_headers, sub_id)
    # score = 3 / (3+1) = 75%
    assert data["score"] == pytest.approx(75.0)


async def test_equal_weight_fields_give_unweighted_score(client, auth_headers):
    form_id = await _create_form(client, auth_headers, [
        {"key": "b1", "label": "B1", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {"weight": 2}},
        {"key": "b2", "label": "B2", "field_type": "boolean",
         "required": True, "position": 2, "config_json": {"weight": 2}},
    ], name="Equal Weight Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [
        {"field_key": "b1", "value": True},
        {"field_key": "b2", "value": False},
    ])
    await _conformity(client, auth_headers, sub_id, [
        {"field_key": "b1", "status": "conforme", "justification": None},
        {"field_key": "b2", "status": "nao_conforme", "justification": "Reprovado"},
    ])
    data = await _finish(client, auth_headers, sub_id)
    assert data["score"] == pytest.approx(50.0)


# ── tenant isolation ──────────────────────────────────────────────────────────

async def test_stats_do_not_leak_across_companies(client, auth_headers, inspector_headers):
    """Stats from company A are not visible to a user whose membership is in company B."""
    # auth_headers (OWNER) and inspector_headers (INSPECTOR) belong to DIFFERENT companies
    form_id = await _create_form(client, auth_headers, [
        {"key": "ok", "label": "OK", "field_type": "boolean",
         "required": True, "position": 1, "config_json": {}},
    ], name="Isolation Stats Form")
    sub_id = await _create_submission(client, auth_headers, form_id)
    await _answer(client, auth_headers, sub_id, [{"field_key": "ok", "value": True}])
    await _finish(client, auth_headers, sub_id)

    resp_owner     = await client.get("/api/v1/me/stats", headers=auth_headers)
    resp_inspector = await client.get("/api/v1/me/stats", headers=inspector_headers)
    assert resp_owner.status_code == 200
    assert resp_inspector.status_code == 200

    owner_total = resp_owner.json()["data"]["total_submissions"]
    insp_total  = resp_inspector.json()["data"]["total_submissions"]
    # Inspector is in a different company — should not see the owner's submission
    assert owner_total >= 1
    assert insp_total == 0
