"""DR-0002 Fases 2-4 / T5 — score e breakdown por componente."""
from backend.tests.integration.test_submissions_component_write import (
    _build_vehicle,
    _form,
    _scoped_bool,
    _submission,
)


async def _answer_all(client, headers, sub_id, rodas, value=True):
    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=headers,
        json={"answers": [{"field_key": "pressao", "value": value, "asset_id": r} for r in rodas]},
    )


async def test_score_sums_each_component_pair(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    await _answer_all(client, auth_headers, sub_id, rodas)
    # 3 conforme + 1 nao_conforme (justificado) → score 75.
    items = [{"field_key": "pressao", "status": "conforme", "asset_id": r} for r in rodas[:3]]
    items.append(
        {
            "field_key": "pressao",
            "status": "nao_conforme",
            "asset_id": rodas[3],
            "justification": "Pneu careca",
        }
    )
    await client.put(
        f"/api/v1/submissions/{sub_id}/conformity", headers=auth_headers, json={"items": items}
    )

    finish = await client.post(f"/api/v1/submissions/{sub_id}/finish", headers=auth_headers)
    assert finish.status_code == 200, finish.text
    data = finish.json()["data"]
    assert data["score"] == 75.0

    bd = data["score_breakdown"]
    assert bd["total_boolean"] == 4
    assert bd["conformes"] == 3
    assert bd["nao_conformes"] == 1
    assert bd["sem_resposta"] == 0


async def test_breakdown_total_reflects_expanded_instances(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    # Avalia apenas 3 dos 4 componentes (não finaliza).
    items = [{"field_key": "pressao", "status": "conforme", "asset_id": r} for r in rodas[:3]]
    res = await client.put(
        f"/api/v1/submissions/{sub_id}/conformity", headers=auth_headers, json={"items": items}
    )
    bd = res.json()["data"]["score_breakdown"]
    # total_boolean = 4 instâncias esperadas (uma por roda), não 1 campo.
    assert bd["total_boolean"] == 4
    assert bd["conformes"] == 3
    assert bd["nao_conformes"] == 0
    assert bd["sem_resposta"] == 1
    # Invariante mantido.
    assert (
        bd["conformes"] + bd["nao_conformes"] + bd["sem_resposta"] + bd["na_count"]
        == bd["total_boolean"]
    )


async def test_score_without_components_unchanged(client, auth_headers):
    # Retrocompat: formulário geral (sem escopo) mantém score/breakdown por campo.
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
    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "geral", "value": True}]},
    )
    await client.put(
        f"/api/v1/submissions/{sub_id}/conformity",
        headers=auth_headers,
        json={"items": [{"field_key": "geral", "status": "conforme"}]},
    )
    finish = await client.post(f"/api/v1/submissions/{sub_id}/finish", headers=auth_headers)
    assert finish.status_code == 200, finish.text
    data = finish.json()["data"]
    assert data["score"] == 100.0
    assert data["score_breakdown"]["total_boolean"] == 1
    assert data["score_breakdown"]["conformes"] == 1
