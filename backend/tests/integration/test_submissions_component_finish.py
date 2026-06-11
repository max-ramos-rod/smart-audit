"""DR-0002 Fases 2-4 / T6 — validação de finalização por instância expandida."""
from backend.tests.integration.test_submissions_component_write import (
    _build_vehicle,
    _form,
    _scoped_bool,
    _submission,
)


async def _finish(client, headers, sub_id):
    return await client.post(f"/api/v1/submissions/{sub_id}/finish", headers=headers)


async def test_finish_blocked_with_pending_component(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    # Responde só 3 das 4 rodas.
    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={
            "answers": [
                {"field_key": "pressao", "value": True, "asset_id": r} for r in rodas[:3]
            ]
        },
    )
    res = await _finish(client, auth_headers, sub_id)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "Campos obrigatorios pendentes" in detail
    assert "pressao" in detail and "Roda 4" in detail  # a roda faltante, com rótulo


async def test_finish_succeeds_when_all_components_answered(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "pressao", "value": True, "asset_id": r} for r in rodas]},
    )
    res = await _finish(client, auth_headers, sub_id)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "completed"


async def test_finish_blocked_when_scoped_field_without_asset(client, auth_headers):
    # Q3: campo escopado em inspeção sem ativo é erro de configuração na finalização.
    _, roda, _ = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id)  # sem asset

    res = await _finish(client, auth_headers, sub_id)
    assert res.status_code == 400
    assert "ativo vinculado" in res.json()["detail"]


async def test_finish_general_required_unanswered_still_blocks(client, auth_headers):
    # Retrocompat: campo geral obrigatório não respondido continua bloqueando.
    form_id = await _form(
        client,
        auth_headers,
        [
            {
                "key": "geral",
                "label": "Geral",
                "field_type": "boolean",
                "required": True,
                "position": 1,
                "config_json": {},
            }
        ],
    )
    sub_id = await _submission(client, auth_headers, form_id)
    res = await _finish(client, auth_headers, sub_id)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "Campos obrigatorios pendentes" in detail and "geral" in detail
