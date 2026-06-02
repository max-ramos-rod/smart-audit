from __future__ import annotations

from datetime import date, datetime

from fpdf import FPDF

_STATUS_LABELS = {
    "draft": "Rascunho",
    "in_progress": "Em andamento",
    "completed": "Concluída",
    "cancelled": "Cancelada",
}

_TYPE_LABELS = {
    "boolean": "Sim/Não",
    "text": "Texto",
    "number": "Número",
    "date": "Data",
    "select": "Seleção",
    "evidence": "Evidências",
    "section": "Seção",
}

# RGB colour palette
_C_BRAND    = (37,  99,  235)   # blue-600
_C_OK       = (22, 163,  74)    # green-600
_C_WARN     = (217, 119,  6)    # amber-600
_C_ERR      = (220,  38,  38)   # red-600
_C_MUTED    = (100, 116, 139)   # slate-500
_C_TEXT     = (15,  23,  42)    # slate-900
_C_BG       = (248, 250, 252)   # slate-50
_C_LINE     = (226, 232, 240)   # slate-200
_C_WHITE    = (255, 255, 255)
_C_SECTION  = (239, 246, 255)   # blue-50


def _score_color(score: float | None) -> tuple[int, int, int]:
    if score is None:
        return _C_MUTED
    return _C_OK if score >= 85 else _C_WARN if score >= 65 else _C_ERR


def _fmt_value(field_type: str, value: object) -> str:
    if value is None or value == "":
        return "-"
    if field_type == "boolean":
        if value == "na":
            return "N/A (não aplicável)"
        return "Sim (conforme)" if value else "Não (não conforme)"
    if field_type == "evidence":
        return "[arquivo anexado]"
    if field_type == "select" and isinstance(value, dict):
        return str(value.get("option", "-"))
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M")


class _PDF(FPDF):
    def __init__(self, company_name: str, form_name: str) -> None:
        super().__init__()
        self._company_name = company_name
        self._form_name = form_name

    def header(self) -> None:
        self.set_fill_color(*_C_BRAND)
        self.set_text_color(*_C_WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 10, "Smart Audit", fill=True, align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_C_TEXT)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_C_MUTED)
        self.cell(0, 8, f"Página {self.page_no()}  ·  Smart Audit", align="C")


def _draw_meta_box(pdf: _PDF, rows: list[tuple[str, str]]) -> None:
    """Two-column key/value grid inside a light background box."""
    col_w = pdf.epw / 2
    pdf.set_fill_color(*_C_BG)
    pdf.set_draw_color(*_C_LINE)
    box_h = (((len(rows) + 1) // 2)) * 7 + 8
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, box_h, style="DF")
    pdf.ln(4)
    for i, (label, value) in enumerate(rows):
        x = pdf.l_margin + 4 if i % 2 == 0 else pdf.l_margin + col_w + 4
        pdf.set_x(x)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_C_MUTED)
        pdf.cell(28, 7, label.upper() + ":", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_C_TEXT)
        pdf.cell(
            col_w - 32, 7, value,
            border=0,
            new_x="LMARGIN" if i % 2 != 0 else "RIGHT",
            new_y="NEXT" if i % 2 != 0 else "TOP",
        )
    if len(rows) % 2 != 0:
        pdf.ln(7)
    pdf.ln(4)


def _draw_score_block(
    pdf: _PDF,
    score: float | None,
    conformes: int,
    nao_conformes: int,
    sem_resposta: int,
    na_count: int,
    total_bool: int,
) -> None:
    """Coloured score badge + breakdown chips on one row."""
    color = _score_color(score)
    label = "N/D" if score is None else (
        "Aprovado" if score >= 85 else "Atenção" if score >= 65 else "Reprovado"
    )
    score_str = "-" if score is None else f"{score:.1f}%"

    # Left: score circle (simulated with a filled rectangle + text)
    box_size = 32
    y0 = pdf.get_y()
    pdf.set_fill_color(*color)
    pdf.set_draw_color(*color)
    pdf.rect(pdf.l_margin, y0, box_size, box_size, style="F")
    pdf.set_text_color(*_C_WHITE)
    pdf.set_font("Helvetica", "B", 12 if score is not None else 16)
    pdf.set_xy(pdf.l_margin, y0 + (box_size - 8) / 2)
    pdf.cell(box_size, 8, score_str, align="C")
    pdf.set_xy(pdf.l_margin, y0 + box_size - 8)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(box_size, 6, label, align="C")

    # Right: 4 chips
    chips = [
        (str(conformes),    "Conformes",    _C_OK),
        (str(nao_conformes),"Não conf.",    _C_ERR),
        (str(sem_resposta), "Sem resp.",    _C_MUTED),
    ]
    if na_count > 0:
        chips.append((str(na_count), "N/A", _C_MUTED))
    if total_bool > 0:
        chips.append((f"/{total_bool}", "Total bool.", _C_TEXT))

    chip_x = pdf.l_margin + box_size + 6
    chip_w = (pdf.epw - box_size - 6) / len(chips)
    for value, chip_label, chip_color in chips:
        pdf.set_xy(chip_x, y0 + 4)
        pdf.set_fill_color(*_C_BG)
        pdf.set_draw_color(*_C_LINE)
        pdf.rect(chip_x, y0, chip_w - 2, box_size, style="DF")
        pdf.set_text_color(*chip_color)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_xy(chip_x, y0 + 6)
        pdf.cell(chip_w - 2, 8, value, align="C")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_C_MUTED)
        pdf.set_xy(chip_x, y0 + 18)
        pdf.cell(chip_w - 2, 6, chip_label, align="C")
        chip_x += chip_w

    pdf.set_xy(pdf.l_margin, y0 + box_size + 4)
    pdf.set_text_color(*_C_TEXT)
    pdf.ln(2)


def generate_submission_pdf(
    *,
    company_name: str,
    form_name: str,
    form_version: int,
    inspector_name: str,
    status: str,
    score: float | None,
    started_at: datetime,
    finished_at: datetime | None,
    fields_with_answers: list[dict],
    score_breakdown: dict | None = None,
) -> bytes:
    pdf = _PDF(company_name=company_name, form_name=form_name)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Title ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(*_C_TEXT)
    pdf.cell(0, 10, form_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_C_MUTED)
    pdf.cell(0, 6, f"Versão {form_version}  ·  {company_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Meta box ─────────────────────────────────────────────────────────
    _draw_meta_box(pdf, [
        ("Status",       _STATUS_LABELS.get(status, status)),
        ("Inspetor",     inspector_name),
        ("Iniciada em",  _fmt_dt(started_at)),
        ("Concluída em", _fmt_dt(finished_at)),
    ])

    # ── Score block ──────────────────────────────────────────────────────
    sb = score_breakdown or {}
    _draw_score_block(
        pdf,
        score=score,
        conformes=sb.get("conformes", 0),
        nao_conformes=sb.get("nao_conformes", 0),
        sem_resposta=sb.get("sem_resposta", 0),
        na_count=sb.get("na_count", 0),
        total_bool=sb.get("total_boolean", 0),
    )
    pdf.ln(4)

    # ── Answers table header ─────────────────────────────────────────────
    col_widths = [8, 68, 22, pdf.epw - 8 - 68 - 22]
    headers = ["#", "Campo", "Tipo", "Resposta"]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*_C_BRAND)
    pdf.set_text_color(*_C_WHITE)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, h, fill=True, border=0)
    pdf.ln()

    # ── Rows ────────────────────────────────────────────────────────────
    row_num = 0
    for row in fields_with_answers:
        field_type = row["field_type"]

        # Section divider
        if field_type == "section":
            pdf.set_fill_color(*_C_SECTION)
            pdf.set_draw_color(*_C_LINE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*_C_BRAND)
            pdf.cell(0, 7, f"  {row['label']}", fill=True, border="B", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*_C_TEXT)
            continue

        fill = row_num % 2 == 0
        pdf.set_fill_color(*(_C_BG if fill else _C_WHITE))
        pdf.set_text_color(*_C_TEXT)
        pdf.set_font("Helvetica", "", 8)

        value = row.get("value")
        answer_text = _fmt_value(field_type, value)

        # Colour boolean answers
        if field_type == "boolean":
            if value is True:
                pdf.set_text_color(*_C_OK)
            elif value is False:
                pdf.set_text_color(*_C_ERR)
            elif value == "na":
                pdf.set_text_color(*_C_MUTED)

        row_data = [
            str(row["position"]),
            row["label"][:40] + ("..." if len(row["label"]) > 40 else ""),
            _TYPE_LABELS.get(field_type, field_type),
            answer_text[:55] + ("..." if len(answer_text) > 55 else ""),
        ]
        for j, (w, text) in enumerate(zip(col_widths, row_data)):
            if j != 3:
                pdf.set_text_color(*_C_TEXT)
            pdf.cell(w, 6, text, fill=fill, border=0)
        pdf.ln()
        pdf.set_text_color(*_C_TEXT)
        row_num += 1

    # ── Footer note ──────────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_C_MUTED)
    total_bool = sb.get("total_boolean", 0)
    pdf.multi_cell(
        0, 5,
        f"Relatório gerado pelo Smart Audit. Score calculado com base em "
        f"{total_bool} campo(s) booleano(s). Formulário: {form_name} v{form_version}.",
    )

    return bytes(pdf.output())
