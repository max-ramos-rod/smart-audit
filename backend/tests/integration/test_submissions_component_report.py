"""DR-0002 Fase 4 / T9 — relatório por componente.

Cobre: o detalhe expõe ``components_snapshot`` (identidade congelada, Q1.1) e o export PDF
expande campos escopados por componente sem quebrar (smoke), lendo o snapshot congelado.
"""

from backend.tests.integration.test_submissions_component_write import (
    _build_vehicle,
    _form,
    _general_bool,
    _scoped_bool,
    _submission,
)


async def _answer_and_conform(client, headers, sub_id, rodas):
    res = await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=headers,
        json={"answers": [{"field_key": "pressao", "value": True, "asset_id": r} for r in rodas]},
    )
    assert res.status_code == 200, res.text
    res = await client.put(
        f"/api/v1/submissions/{sub_id}/conformity",
        headers=headers,
        json={
            "items": [{"field_key": "pressao", "status": "conforme", "asset_id": r} for r in rodas]
        },
    )
    assert res.status_code == 200, res.text


async def test_detail_exposes_components_snapshot(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)
    await _answer_and_conform(client, auth_headers, sub_id, rodas)

    got = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_headers)
    detail = got.json()["data"]
    snapshot = detail["components_snapshot"]
    assert snapshot is not None
    assert set(snapshot.keys()) == set(rodas)
    sample = snapshot[rodas[0]]
    assert sample["type"] == "Roda"
    assert sample["label"].startswith("Roda ")
    assert sample["path"].startswith("Caminhao ABC > Roda ")


async def test_detail_without_components_has_null_snapshot(client, auth_headers):
    # Formulário sem campo escopado → sem snapshot (retrocompat).
    form_id = await _form(client, auth_headers, [_general_bool()])
    sub_id = await _submission(client, auth_headers, form_id)
    got = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_headers)
    detail = got.json()["data"]
    assert detail["components_snapshot"] is None


async def test_export_pdf_with_components(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)
    await _answer_and_conform(client, auth_headers, sub_id, rodas)
    assert (
        await client.post(f"/api/v1/submissions/{sub_id}/finish", headers=auth_headers)
    ).status_code == 200

    res = await client.get(f"/api/v1/submissions/{sub_id}/export", headers=auth_headers)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content[:4] == b"%PDF"
