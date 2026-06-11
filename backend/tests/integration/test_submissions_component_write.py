"""DR-0002 Fases 2-4 / T4 — escrita por componente (asset_id em save_answers/conformity).

Cobre: upsert por (submission, field, asset_id), answers_json aninhado (valores puros),
components_snapshot congelado 1x por componente (INV6), e validação de escopo (INV1/INV2).
"""
from sqlalchemy import func, select

from app.db.models.submission_values import SubmissionValue
from app.db.models.submissions import Submission
from backend.tests.integration.test_auth import assert_problem


async def _type(client, headers, name: str) -> str:
    res = await client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _asset(client, headers, type_id, identifier, parent=None) -> str:
    body: dict = {"asset_type_id": type_id, "identifier": identifier}
    if parent is not None:
        body["parent_asset_id"] = parent
    res = await client.post("/api/v1/assets", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _form(client, headers, fields) -> str:
    res = await client.post(
        "/api/v1/forms", headers=headers, json={"name": "Form T4", "fields": fields}
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


async def _submission(client, headers, form_id, asset_id=None) -> str:
    body: dict = {"form_id": form_id}
    if asset_id is not None:
        body["asset_id"] = asset_id
    res = await client.post("/api/v1/submissions", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


def _scoped_bool(type_id, key="pressao", pos=1) -> dict:
    return {
        "key": key,
        "label": "Pressao",
        "field_type": "boolean",
        "required": True,
        "position": pos,
        "config_json": {},
        "component_type_id": type_id,
    }


def _general_bool(key="geral", pos=9) -> dict:
    return {
        "key": key,
        "label": "Geral",
        "field_type": "boolean",
        "required": False,
        "position": pos,
        "config_json": {},
    }


async def _build_vehicle(client, headers):
    """Veículo com 4 rodas. Retorna (root_id, roda_type, [roda_ids])."""
    veiculo = await _type(client, headers, "Veiculo")
    roda = await _type(client, headers, "Roda")
    root = await _asset(client, headers, veiculo, "Caminhao ABC")
    rodas = [await _asset(client, headers, roda, f"Roda {p}", parent=root) for p in "1234"]
    return root, roda, rodas


async def test_save_answers_per_component(client, auth_headers, db_session):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    res = await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "pressao", "value": True, "asset_id": r} for r in rodas]},
    )
    assert res.status_code == 200, res.text

    # 4 linhas relacionais.
    count = await db_session.scalar(
        select(func.count())
        .select_from(SubmissionValue)
        .where(SubmissionValue.submission_id == sub_id)
    )
    assert count == 4

    # answers_json aninhado (valores puros) + components_snapshot congelado.
    row = (
        await db_session.execute(
            select(Submission.answers_json, Submission.components_snapshot).where(
                Submission.id == sub_id
            )
        )
    ).one()
    answers_json, components_snapshot = row
    assert set(answers_json["pressao"].keys()) == set(rodas)
    assert all(v is True for v in answers_json["pressao"].values())
    assert set(components_snapshot.keys()) == set(rodas)
    sample = components_snapshot[rodas[0]]
    assert sample["type"] == "Roda"
    assert sample["label"].startswith("Roda ")
    assert sample["path"].startswith("Caminhao ABC > Roda ")

    # API expõe asset_id por resposta.
    detail = (await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_headers)).json()["data"]
    pressao_answers = [a for a in detail["answers"] if a["field_key"] == "pressao"]
    assert {a["asset_id"] for a in pressao_answers} == set(rodas)


async def test_save_conformity_per_component(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    res = await client.put(
        f"/api/v1/submissions/{sub_id}/conformity",
        headers=auth_headers,
        json={
            "items": [
                {"field_key": "pressao", "status": "conforme", "asset_id": r} for r in rodas
            ]
        },
    )
    assert res.status_code == 200, res.text
    detail = (await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_headers)).json()["data"]
    pressao = [c for c in detail["conformity"] if c["field_key"] == "pressao"]
    assert {c["asset_id"] for c in pressao} == set(rodas)


async def test_answer_asset_outside_tree_rejected(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    # Roda de OUTRO veículo (fora da subárvore do alvo).
    other_root = await _asset(client, auth_headers, roda, "Outro Veiculo")
    foreign_roda = await _asset(client, auth_headers, roda, "Roda Estranha", parent=other_root)

    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    assert_problem(
        await client.put(
            f"/api/v1/submissions/{sub_id}/answers",
            headers=auth_headers,
            json={"answers": [{"field_key": "pressao", "value": True, "asset_id": foreign_roda}]},
        ),
        400,
        "Componente invalido para o campo pressao.",
    )


async def test_answer_wrong_component_type_rejected(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    porta = await _type(client, auth_headers, "Porta")
    porta_asset = await _asset(client, auth_headers, porta, "Porta DD", parent=root)

    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    # asset existe na subárvore, mas é do tipo errado.
    assert_problem(
        await client.put(
            f"/api/v1/submissions/{sub_id}/answers",
            headers=auth_headers,
            json={"answers": [{"field_key": "pressao", "value": True, "asset_id": porta_asset}]},
        ),
        400,
        "Componente invalido para o campo pressao.",
    )


async def test_general_field_with_asset_id_rejected(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_general_bool(key="geral", pos=1)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    assert_problem(
        await client.put(
            f"/api/v1/submissions/{sub_id}/answers",
            headers=auth_headers,
            json={"answers": [{"field_key": "geral", "value": True, "asset_id": rodas[0]}]},
        ),
        400,
        "Campo geral nao aceita escopo de componente.",
    )


async def test_scoped_field_without_asset_id_rejected(client, auth_headers):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)

    assert_problem(
        await client.put(
            f"/api/v1/submissions/{sub_id}/answers",
            headers=auth_headers,
            json={"answers": [{"field_key": "pressao", "value": True}]},
        ),
        400,
        "Campo pressao exige um componente.",
    )


async def test_components_snapshot_frozen_after_rename(client, auth_headers, db_session):
    root, roda, rodas = await _build_vehicle(client, auth_headers)
    form_id = await _form(client, auth_headers, [_scoped_bool(roda)])
    sub_id = await _submission(client, auth_headers, form_id, asset_id=root)
    target = rodas[0]

    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "pressao", "value": True, "asset_id": target}]},
    )
    # Renomeia o componente.
    rename = await client.patch(
        f"/api/v1/assets/{target}", headers=auth_headers, json={"identifier": "Roda Renomeada"}
    )
    assert rename.status_code == 200, rename.text
    # Reescreve a resposta — o snapshot de identidade NÃO deve mudar (INV6).
    await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "pressao", "value": False, "asset_id": target}]},
    )

    snapshot = await db_session.scalar(
        select(Submission.components_snapshot).where(Submission.id == sub_id)
    )
    assert snapshot[target]["label"] == "Roda 1"  # rótulo original congelado


async def test_general_field_snapshot_is_scalar(client, auth_headers, db_session):
    # Retrocompat: campo geral mantém answers_json escalar e asset_id NULL.
    form_id = await _form(client, auth_headers, [_general_bool(key="geral", pos=1)])
    sub_id = await _submission(client, auth_headers, form_id)

    res = await client.put(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=auth_headers,
        json={"answers": [{"field_key": "geral", "value": True}]},
    )
    assert res.status_code == 200, res.text

    row = (
        await db_session.execute(
            select(Submission.answers_json, Submission.components_snapshot).where(
                Submission.id == sub_id
            )
        )
    ).one()
    answers_json, components_snapshot = row
    assert answers_json["geral"] is True  # escalar, não dict
    assert components_snapshot is None
