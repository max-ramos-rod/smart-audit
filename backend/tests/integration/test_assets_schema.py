"""Schema-level guarantees for the assets/clients/asset_types tables (DR-0001 Fase 1, T1).

Valida os CHECKs de `assets` no nível do banco:
- ck_assets_client_only_on_root (M6): componente não pode ter client_id.
- ck_assets_status: status restrito a active/inactive/retired.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.asset_types import AssetType
from app.db.models.assets import Asset
from app.db.models.clients import Client


async def test_valid_asset_tree_persists(db_session, seeded_user):
    """Raiz com client_id e componente sem client_id são válidos."""
    company_id = seeded_user["company_id"]
    client = Client(company_id=company_id, name="Cliente X")
    atype = AssetType(company_id=company_id, name="Veículo")
    db_session.add_all([client, atype])
    await db_session.flush()

    root = Asset(
        company_id=company_id,
        asset_type_id=atype.id,
        identifier="Placa ABC-1234",
        client_id=client.id,
    )
    db_session.add(root)
    await db_session.flush()

    component = Asset(
        company_id=company_id,
        asset_type_id=atype.id,
        identifier="Roda DD",
        parent_asset_id=root.id,
    )
    db_session.add(component)
    await db_session.flush()

    assert root.status == "active"
    assert root.client_id == client.id
    assert component.parent_asset_id == root.id
    assert component.client_id is None
    assert component.attributes_json == {}


async def test_component_cannot_have_client_id(db_session, seeded_user):
    """ck_assets_client_only_on_root: componente (com pai) + client_id é rejeitado."""
    company_id = seeded_user["company_id"]
    client = Client(company_id=company_id, name="Cliente Y")
    atype = AssetType(company_id=company_id, name="Veículo")
    db_session.add_all([client, atype])
    await db_session.flush()

    root = Asset(company_id=company_id, asset_type_id=atype.id, identifier="Placa DEF-5678")
    db_session.add(root)
    await db_session.flush()

    bad_component = Asset(
        company_id=company_id,
        asset_type_id=atype.id,
        identifier="Roda DE",
        parent_asset_id=root.id,
        client_id=client.id,
    )
    db_session.add(bad_component)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_invalid_status_rejected(db_session, seeded_user):
    """ck_assets_status: status fora de {active,inactive,retired} é rejeitado."""
    company_id = seeded_user["company_id"]
    atype = AssetType(company_id=company_id, name="Apartamento")
    db_session.add(atype)
    await db_session.flush()

    bad_asset = Asset(
        company_id=company_id,
        asset_type_id=atype.id,
        identifier="Ap 302",
        status="bogus",
    )
    db_session.add(bad_asset)
    with pytest.raises(IntegrityError):
        await db_session.flush()
