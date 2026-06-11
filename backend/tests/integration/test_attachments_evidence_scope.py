"""DR-0017 fase EXPAND — esquema da âncora de evidências por escopo.

Valida, no nível do banco: (a) INV-E1/Q7.3 — a âncora é NÃO-única, então um item
inspecionado admite N evidências; (b) as novas colunas da âncora são graváveis e
``submission_value_id`` é opcional nesta fase (deprecado).
"""

from sqlalchemy import func, select

from app.db.models.attachments import Attachment
from app.db.models.form_fields import FormField
from backend.tests.integration.test_submissions_component_write import (
    _form,
    _general_bool,
    _submission,
)


async def _field_id(db, key: str) -> str:
    return await db.scalar(select(FormField.id).where(FormField.key == key))


async def test_anchor_is_non_unique_n_evidences_per_item(
    client, auth_headers, seeded_user, db_session
):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    field_id = await _field_id(db_session, "geral")

    # INV-E1 / Q7.3: mesma âncora (submission, field, asset=NULL) aceita N anexos.
    for i in range(3):
        db_session.add(
            Attachment(
                company_id=seeded_user["company_id"],
                scope="field",
                submission_id=sub_id,
                form_field_id=field_id,
                asset_id=None,
                file_url=f"http://x/foto{i}.jpg",
                mime_type="image/jpeg",
                file_size=100,
                uploaded_by=seeded_user["user_id"],
            )
        )
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count()).select_from(Attachment).where(Attachment.submission_id == sub_id)
    )
    assert count == 3  # nenhuma constraint de unicidade limitou N


async def test_new_anchor_columns_writable_and_legacy_link_optional(
    client, auth_headers, seeded_user, db_session
):
    form_id = await _form(client, auth_headers, [_general_bool(key="geral")])
    sub_id = await _submission(client, auth_headers, form_id)
    field_id = await _field_id(db_session, "geral")

    att = Attachment(
        company_id=seeded_user["company_id"],
        scope="field",
        submission_id=sub_id,
        form_field_id=field_id,
        asset_id=None,
        component_label=None,
        metadata_json={"tipo_doc": "laudo"},
        file_url="http://x/a.pdf",
        mime_type="application/pdf",
        file_size=1,
        uploaded_by=seeded_user["user_id"],
        submission_value_id=None,  # vínculo legado é opcional na fase EXPAND
    )
    db_session.add(att)
    await db_session.commit()

    got = await db_session.scalar(select(Attachment).where(Attachment.id == att.id))
    assert got.scope == "field"
    assert got.metadata_json == {"tipo_doc": "laudo"}
    assert got.submission_value_id is None
