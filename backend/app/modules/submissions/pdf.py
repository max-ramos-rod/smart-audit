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
    "photo": "Foto",
}


def _fmt_value(field_type: str, value: object) -> str:
    if value is None:
        return "—"
    if field_type == "boolean":
        return "Sim" if value else "Não"
    if field_type == "select" and isinstance(value, dict):
        return str(value.get("option", "—"))
    if field_type == "photo":
        return "[foto anexada]"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M")


class _PDF(FPDF):
    def __init__(self, company_name: str, form_name: str) -> None:
        super().__init__()
        self._company_name = company_name
        self._form_name = form_name

    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(245, 158, 11)  # amber-500
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "Smart Audit", fill=True, align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


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
) -> bytes:
    pdf = _PDF(company_name=company_name, form_name=form_name)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, form_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Versão {form_version}  ·  {company_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Metadata box
    pdf.set_fill_color(249, 250, 251)
    pdf.set_draw_color(229, 231, 235)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)

    meta_rows = [
        ("Status", _STATUS_LABELS.get(status, status)),
        ("Score", f"{score:.1f}%" if score is not None else "—"),
        ("Inspetor", inspector_name),
        ("Iniciada em", _fmt_dt(started_at)),
        ("Finalizada em", _fmt_dt(finished_at)),
    ]
    col_w = (pdf.epw) / 2
    for i, (label, value) in enumerate(meta_rows):
        x = pdf.l_margin if i % 2 == 0 else pdf.l_margin + col_w
        if i % 2 == 0 and i > 0:
            pass
        pdf.set_x(x)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 7, label + ":", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w - 30, 7, value, border=0, new_x="LMARGIN" if i % 2 != 0 else "RIGHT",
                 new_y="NEXT" if i % 2 != 0 else "TOP")
    if len(meta_rows) % 2 != 0:
        pdf.ln(7)
    pdf.ln(6)

    # Answers table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(255, 255, 255)
    col_widths = [8, 70, 22, pdf.epw - 8 - 70 - 22]
    headers = ["#", "Campo", "Tipo", "Resposta"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, h, fill=True, border=0)
    pdf.ln()

    pdf.set_text_color(30, 30, 30)
    for i, row in enumerate(fields_with_answers):
        fill = i % 2 == 0
        pdf.set_fill_color(249, 250, 251) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 9)
        answer_text = _fmt_value(row["field_type"], row["value"])
        row_data = [
            str(row["position"]),
            row["label"][:45] + ("…" if len(row["label"]) > 45 else ""),
            _TYPE_LABELS.get(row["field_type"], row["field_type"]),
            answer_text[:60] + ("…" if len(answer_text) > 60 else ""),
        ]
        for w, text in zip(col_widths, row_data):
            pdf.cell(w, 6, text, fill=fill, border=0)
        pdf.ln()

    return bytes(pdf.output())
