"""
Seed: Formulario de Inspecao Veicular

Cria o formulario com 8 secoes e ~50 campos no primeiro company ativo encontrado.
Se o formulario ja existir (pelo nome exato), o script cancela sem duplicar.

Uso:
    python backend/scripts/seed_inspecao_veicular.py
    python backend/scripts/seed_inspecao_veicular.py --company-slug minha-empresa
"""

import argparse
import asyncio
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models.companies import Company
from app.db.models.form_fields import FormField
from app.db.models.form_versions import FormVersion
from app.db.models.forms import Form
from app.db.models.memberships import Membership


# ---------------------------------------------------------------------------
# Definicao do formulario
# ---------------------------------------------------------------------------

FORM_NAME = "Inspecao Veicular"
FORM_DESC = "Formulario completo de inspecao veicular por secoes: identificacao, carroceria, motor, interior e documentacao."

# Cada item e um dict com:
#   type="section" -> { "type": "section", "label": "..." }
#   type=outros    -> { "key", "label", "field_type", "required", "weight", "allow_na" }

FIELDS: list[dict] = [
    # ── Identificacao ──────────────────────────────────────────────────────
    {"type": "section",  "label": "Identificacao"},
    {"key": "placa",        "label": "Placa do veiculo",       "field_type": "text",    "required": True},
    {"key": "modelo",       "label": "Modelo / Marca",         "field_type": "text",    "required": True},
    {"key": "ano",          "label": "Ano de fabricacao",      "field_type": "number",  "required": True},
    {"key": "km",           "label": "Quilometragem atual",    "field_type": "number",  "required": True},
    {"key": "inspetor",     "label": "Nome do inspetor",       "field_type": "text",    "required": True},
    {"key": "data_insp",    "label": "Data da inspecao",       "field_type": "date",    "required": True},
    {"key": "id_foto",      "label": "Foto geral do veiculo",  "field_type": "evidence"},

    # ── Dianteira ──────────────────────────────────────────────────────────
    {"type": "section",  "label": "Dianteira"},
    {"key": "di_parachoque",  "label": "Para-choque dianteiro integro",        "field_type": "boolean", "weight": 2},
    {"key": "di_farol_baixo", "label": "Farois baixos funcionando",            "field_type": "boolean", "required": True, "weight": 3},
    {"key": "di_farol_alto",  "label": "Farois altos funcionando",             "field_type": "boolean", "required": True, "weight": 2},
    {"key": "di_setas",       "label": "Setas dianteiras funcionando",         "field_type": "boolean", "required": True, "weight": 2},
    {"key": "di_limpador",    "label": "Limpadores de para-brisa funcionando", "field_type": "boolean", "required": True, "weight": 2},
    {"key": "di_parabrisa",   "label": "Para-brisa sem trincas ou rachaduras", "field_type": "boolean", "required": True, "weight": 3},
    {"key": "di_foto",        "label": "Foto da dianteira",                    "field_type": "evidence"},

    # ── Lateral Esquerda ───────────────────────────────────────────────────
    {"type": "section",  "label": "Lateral Esquerda"},
    {"key": "le_retrovisor",  "label": "Espelho retrovisor esquerdo integro",            "field_type": "boolean", "required": True, "weight": 2},
    {"key": "le_pneu_diant",  "label": "Pneu dianteiro esquerdo em boas condicoes",     "field_type": "boolean", "required": True, "weight": 3},
    {"key": "le_pneu_tras",   "label": "Pneu traseiro esquerdo em boas condicoes",      "field_type": "boolean", "required": True, "weight": 3},
    {"key": "le_lataria",     "label": "Lataria esquerda sem avarias significativas",   "field_type": "boolean", "weight": 1, "allow_na": True},
    {"key": "le_foto",        "label": "Foto lateral esquerda",                         "field_type": "evidence"},

    # ── Lateral Direita ────────────────────────────────────────────────────
    {"type": "section",  "label": "Lateral Direita"},
    {"key": "ld_retrovisor",  "label": "Espelho retrovisor direito integro",            "field_type": "boolean", "required": True, "weight": 2},
    {"key": "ld_pneu_diant",  "label": "Pneu dianteiro direito em boas condicoes",     "field_type": "boolean", "required": True, "weight": 3},
    {"key": "ld_pneu_tras",   "label": "Pneu traseiro direito em boas condicoes",      "field_type": "boolean", "required": True, "weight": 3},
    {"key": "ld_lataria",     "label": "Lataria direita sem avarias significativas",   "field_type": "boolean", "weight": 1, "allow_na": True},
    {"key": "ld_foto",        "label": "Foto lateral direita",                         "field_type": "evidence"},

    # ── Traseira ───────────────────────────────────────────────────────────
    {"type": "section",  "label": "Traseira"},
    {"key": "tr_parachoque",  "label": "Para-choque traseiro integro",       "field_type": "boolean", "weight": 2},
    {"key": "tr_lanterna",    "label": "Lanternas traseiras funcionando",    "field_type": "boolean", "required": True, "weight": 3},
    {"key": "tr_luz_freio",   "label": "Luz de freio funcionando",           "field_type": "boolean", "required": True, "weight": 3},
    {"key": "tr_luz_re",      "label": "Luz de re funcionando",              "field_type": "boolean", "required": True, "weight": 2},
    {"key": "tr_setas",       "label": "Setas traseiras funcionando",        "field_type": "boolean", "required": True, "weight": 2},
    {"key": "tr_foto",        "label": "Foto da traseira",                   "field_type": "evidence"},

    # ── Motor ──────────────────────────────────────────────────────────────
    {"type": "section",  "label": "Motor"},
    {"key": "mo_oleo",        "label": "Nivel de oleo adequado",               "field_type": "boolean", "required": True, "weight": 3},
    {"key": "mo_agua",        "label": "Nivel de arrefecimento adequado",      "field_type": "boolean", "required": True, "weight": 2},
    {"key": "mo_correia",     "label": "Correia dentada em bom estado",        "field_type": "boolean", "required": True, "weight": 3},
    {"key": "mo_vazamento",   "label": "Sem vazamentos visiveis",              "field_type": "boolean", "required": True, "weight": 3},
    {"key": "mo_bateria",     "label": "Bateria em bom estado",                "field_type": "boolean", "required": True, "weight": 2},
    {"key": "mo_foto",        "label": "Foto do compartimento do motor",       "field_type": "evidence", "required": True},

    # ── Interior ───────────────────────────────────────────────────────────
    {"type": "section",  "label": "Interior"},
    {"key": "in_cinto_mot",   "label": "Cinto de seguranca do motorista funcionando",    "field_type": "boolean", "required": True, "weight": 3},
    {"key": "in_cinto_pass",  "label": "Cintos dos passageiros funcionando",             "field_type": "boolean", "required": True, "weight": 2},
    {"key": "in_freio_mao",   "label": "Freio de mao funcionando",                      "field_type": "boolean", "required": True, "weight": 3},
    {"key": "in_airbag",      "label": "Airbag sem luz de aviso no painel",             "field_type": "boolean", "required": True, "weight": 3},
    {"key": "in_ac",          "label": "Ar-condicionado funcionando",                   "field_type": "boolean", "weight": 1, "allow_na": True},
    {"key": "in_extintor",    "label": "Extintor de incendio presente e dentro validade", "field_type": "boolean", "required": True, "weight": 3},
    {"key": "in_triangulo",   "label": "Triangulo de sinalizacao presente",             "field_type": "boolean", "required": True, "weight": 2},
    {"key": "in_estepe",      "label": "Estepe em boas condicoes",                      "field_type": "boolean", "required": True, "weight": 2},
    {"key": "in_macaco",      "label": "Macaco e chave de roda presentes",              "field_type": "boolean", "required": True, "weight": 1},
    {"key": "in_foto",        "label": "Foto do interior",                              "field_type": "evidence"},

    # ── Documentacao ──────────────────────────────────────────────────────
    {"type": "section",  "label": "Documentacao"},
    {"key": "do_crlv",        "label": "CRLV (licenciamento) em dia",    "field_type": "boolean", "required": True, "weight": 3},
    {"key": "do_seguro",      "label": "Seguro obrigatorio em dia",      "field_type": "boolean", "required": True, "weight": 2},
    {"key": "do_tacografo",   "label": "Tacografo aferido",              "field_type": "boolean", "weight": 3, "allow_na": True},
    {"key": "do_obs",         "label": "Observacoes gerais",             "field_type": "text"},
    {"key": "do_foto",        "label": "Foto da documentacao",           "field_type": "evidence"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_config(item: dict) -> dict:
    cfg: dict = {}
    if item.get("weight"):
        cfg["weight"] = float(item["weight"])
    if item.get("allow_na"):
        cfg["allow_na"] = True
    return cfg


async def run(company_slug: str | None) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async with AsyncSession(engine, expire_on_commit=False) as db:
        # ── Encontrar company ──────────────────────────────────────────────
        if company_slug:
            stmt = select(Company).where(Company.slug == company_slug, Company.is_active == True)
        else:
            stmt = select(Company).where(Company.is_active == True).limit(1)
        company = (await db.execute(stmt)).scalar_one_or_none()

        if company is None:
            raise SystemExit(
                f"Nenhuma empresa ativa encontrada"
                + (f" com slug '{company_slug}'" if company_slug else "")
                + ". Crie uma empresa antes de executar este script."
            )

        print(f"Empresa: {company.name} ({company.slug})")

        # ── Encontrar owner ────────────────────────────────────────────────
        membership = (await db.execute(
            select(Membership)
            .where(Membership.company_id == company.id, Membership.role == "OWNER")
            .limit(1)
        )).scalar_one_or_none()

        if membership is None:
            raise SystemExit(f"Nenhum OWNER encontrado para '{company.name}'.")

        user_id = str(membership.user_id)
        print(f"Criando como user_id={user_id}")

        # ── Verificar duplicata ────────────────────────────────────────────
        existing = (await db.execute(
            select(Form).where(Form.company_id == company.id, Form.name == FORM_NAME)
        )).scalar_one_or_none()

        if existing is not None:
            print(f"Formulario '{FORM_NAME}' ja existe (id={existing.id}). Nada a fazer.")
            return

        # ── Criar Form ─────────────────────────────────────────────────────
        form = Form(
            company_id=str(company.id),
            name=FORM_NAME,
            description=FORM_DESC,
            is_active=True,
            created_by=user_id,
        )
        db.add(form)
        await db.flush()

        # ── Criar FormVersion ──────────────────────────────────────────────
        version = FormVersion(
            form_id=str(form.id),
            version=1,
            status="published",
            published_at=datetime.now(UTC),
            created_by=user_id,
        )
        db.add(version)
        await db.flush()

        # ── Criar FormFields ───────────────────────────────────────────────
        position = 0
        section_counter = 0
        field_count = 0

        for item in FIELDS:
            position += 1

            if item.get("type") == "section":
                section_counter += 1
                key = f"__section_{position}__"
                field = FormField(
                    form_version_id=str(version.id),
                    key=key,
                    label=item["label"],
                    field_type="section",
                    required=False,
                    position=position,
                    config_json={},
                )
            else:
                field = FormField(
                    form_version_id=str(version.id),
                    key=item["key"],
                    label=item["label"],
                    field_type=item["field_type"],
                    required=item.get("required", False),
                    position=position,
                    config_json=_build_config(item),
                )
                field_count += 1

            db.add(field)

        await db.commit()

        print(f"")
        print(f"  Formulario criado com sucesso!")
        print(f"  Nome    : {FORM_NAME}")
        print(f"  ID      : {form.id}")
        print(f"  Versao  : v1 (publicada)")
        print(f"  Secoes  : {section_counter}")
        print(f"  Campos  : {field_count}")
        print(f"  Total de posicoes: {position}")
        print(f"")
        print(f"  Acesse em: /forms/{form.id}")

    await engine.dispose()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed: Formulario de Inspecao Veicular")
    parser.add_argument("--company-slug", default=None, help="Slug da empresa (padrao: primeira ativa)")
    args = parser.parse_args()
    asyncio.run(run(args.company_slug))
