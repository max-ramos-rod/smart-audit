"""Parse CSV/Excel files into FormCreateRequest for form import."""
from __future__ import annotations

import csv
import io
import re
import unicodedata

from fastapi import HTTPException, status

from app.modules.forms.schemas import FormCreateRequest, FormFieldCreateRequest

_TIPO_MAP = {
    "sim_nao": "boolean",
    "boolean": "boolean",
    "texto": "text",
    "text": "text",
    "numero": "number",
    "número": "number",
    "number": "number",
    "data": "date",
    "date": "date",
    "selecao": "select",
    "seleção": "select",
    "select": "select",
    "secao": "section",
    "seção": "section",
    "section": "section",
}

_REQUIRED_COLS = {"label", "tipo"}


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^\w\s-]", "", ascii_text).strip().lower()
    slug = re.sub(r"[\s\-]+", "_", slug)
    return slug[:80] or "campo"


def _unique_key(base: str, seen: set[str]) -> str:
    key = base
    counter = 2
    while key in seen:
        key = f"{base}_{counter}"
        counter += 1
    seen.add(key)
    return key


def _bool_col(value: str) -> bool:
    return value.strip().lower() in ("sim", "yes", "true", "1", "s")


def _parse_rows(rows: list[dict[str, str]], form_name: str) -> FormCreateRequest:
    fields: list[FormFieldCreateRequest] = []
    seen_keys: set[str] = set()

    for row_num, row in enumerate(rows, start=2):
        label = (row.get("label") or "").strip()
        tipo_raw = (row.get("tipo") or "").strip().lower()

        if not label and not tipo_raw:
            continue
        if not label:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Linha {row_num}: coluna 'label' vazia.",
            )
        if not tipo_raw:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Linha {row_num}: coluna 'tipo' vazia.",
            )

        field_type = _TIPO_MAP.get(tipo_raw)
        if field_type is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Linha {row_num}: tipo '{tipo_raw}' inválido. "
                    "Use: sim_nao, texto, numero, data, selecao, secao."
                ),
            )

        instruction_raw = (row.get("instrucao") or row.get("instrução") or "").strip()
        instruction = instruction_raw[:1000] if instruction_raw else None

        if field_type == "section":
            key = _unique_key(f"__section_{len(fields) + 1}__", seen_keys)
            fields.append(FormFieldCreateRequest(
                key=key,
                label=label[:180],
                field_type="section",
                required=False,
                position=len(fields) + 1,
                config_json={},
                instruction=instruction,
            ))
            continue

        obrigatorio_raw = (row.get("obrigatorio") or row.get("obrigatório") or "sim").strip()
        required = _bool_col(obrigatorio_raw)

        config: dict = {}

        if field_type == "boolean":
            peso_raw = (row.get("peso") or "").strip()
            if peso_raw:
                try:
                    weight = float(peso_raw)
                    if weight != 1.0:
                        config["weight"] = weight
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Linha {row_num}: 'peso' deve ser um número.",
                    )
            permite_na_raw = (row.get("permite_na") or row.get("permite na") or "nao").strip()
            if _bool_col(permite_na_raw):
                config["allow_na"] = True

        if field_type == "select":
            opcoes_raw = (row.get("opcoes") or row.get("opções") or "").strip()
            if not opcoes_raw:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Linha {row_num}: campo do tipo 'selecao' exige coluna 'opcoes'.",
                )
            options = [o.strip() for o in opcoes_raw.split(";") if o.strip()]
            if not options:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Linha {row_num}: 'opcoes' não pode ser vazia para tipo 'selecao'.",
                )
            config["options"] = options

        base_key = _slugify(label)
        key = _unique_key(base_key, seen_keys)

        fields.append(FormFieldCreateRequest(
            key=key,
            label=label[:180],
            field_type=field_type,
            required=required,
            position=len(fields) + 1,
            config_json=config,
            instruction=instruction,
        ))

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="O arquivo não contém nenhum campo válido.",
        )

    return FormCreateRequest(name=form_name[:180], fields=fields)


def _normalise_headers(raw_headers: list[str]) -> list[str]:
    return [h.strip().lower() for h in raw_headers]


def parse_csv(content: bytes, form_name: str) -> FormCreateRequest:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV sem cabeçalho.",
        )
    normalised = _normalise_headers(list(reader.fieldnames))
    missing = _REQUIRED_COLS - set(normalised)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"CSV sem coluna(s) obrigatória(s): {', '.join(sorted(missing))}.",
        )
    rows = [{normalised[i]: v for i, v in enumerate(row.values())} for row in reader]
    return _parse_rows(rows, form_name)


def parse_excel(content: bytes, form_name: str) -> FormCreateRequest:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    raw_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not raw_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Planilha vazia.",
        )

    headers = _normalise_headers([str(c) if c is not None else "" for c in raw_rows[0]])
    missing = _REQUIRED_COLS - set(headers)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Planilha sem coluna(s) obrigatória(s): {', '.join(sorted(missing))}.",
        )

    rows: list[dict[str, str]] = []
    for raw in raw_rows[1:]:
        row = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(raw) if i < len(headers)}
        rows.append(row)

    return _parse_rows(rows, form_name)


def parse_import_file(content: bytes, filename: str, form_name: str | None) -> FormCreateRequest:
    name = (form_name or "").strip() or filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("xlsx", "xls", "xlsm"):
        return parse_excel(content, name)
    if ext == "csv":
        return parse_csv(content, name)
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Formato não suportado. Envie um arquivo .csv ou .xlsx.",
    )
