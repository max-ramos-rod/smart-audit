import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine


async def main():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Find forms with 'veicular' in name
        r = await db.execute(text(
            "SELECT id, name FROM forms WHERE name ILIKE '%veicular%' OR name ILIKE '%veiculo%' ORDER BY created_at DESC LIMIT 5"
        ))
        forms = r.fetchall()
        if not forms:
            print("Nenhum formulário veicular encontrado.")
            r2 = await db.execute(text("SELECT id, name FROM forms ORDER BY created_at DESC LIMIT 10"))
            print("Últimos formulários:")
            for row in r2.fetchall():
                print(f"  {row.id}  {row.name}")
            return

        for form in forms:
            print(f"\n=== Formulário: {form.name} (id={form.id}) ===")
            # Get latest version
            rv = await db.execute(text(
                "SELECT id, version FROM form_versions WHERE form_id = :fid ORDER BY version DESC LIMIT 1"
            ), {"fid": str(form.id)})
            ver = rv.fetchone()
            if not ver:
                print("  Sem versão")
                continue
            print(f"  Versão {ver.version} (id={ver.id})")

            # Count fields by type
            rf = await db.execute(text(
                "SELECT field_type, COUNT(*) as cnt FROM form_fields WHERE form_version_id = :vid GROUP BY field_type ORDER BY field_type"
            ), {"vid": str(ver.id)})
            totals = rf.fetchall()
            grand_total = 0
            for t in totals:
                print(f"  {t.field_type}: {t.cnt}")
                grand_total += t.cnt
            print(f"  TOTAL: {grand_total}")


asyncio.run(main())
