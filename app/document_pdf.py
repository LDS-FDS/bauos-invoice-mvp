from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_HEADER_BG = colors.HexColor("#6fb0c2")
_ROW_BG = colors.HexColor("#fffdf8")
_ALT_ROW_BG = colors.HexColor("#f4ede1")
_BORDER = colors.HexColor("#e6dcc9")
_TEXT_MUTED = colors.HexColor("#8a8275")


def _fmt_amount(value: float | None, currency: str = "EUR") -> str:
    if value is None:
        return "-"
    return f"{value:.2f} {currency}".strip()


def build_document_pdf(document: dict, company: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=document["doc_number"],
    )

    styles = getSampleStyleSheet()
    muted_style = ParagraphStyle(
        "muted", parent=styles["Normal"], textColor=_TEXT_MUTED, fontSize=9
    )

    doc_type_label = "ANGEBOT" if document["doc_type"] == "angebot" else "RECHNUNG"
    customer = document.get("customer") or {}
    currency = "EUR"

    company_lines = [
        company.get("name"),
        company.get("street"),
        f"{company.get('zip_code') or ''} {company.get('city') or ''}".strip(),
    ]
    company_lines = [line for line in company_lines if line]

    customer_lines = [
        customer.get("name"),
        customer.get("street"),
        f"{customer.get('zip_code') or ''} {customer.get('city') or ''}".strip(),
    ]
    customer_lines = [line for line in customer_lines if line]

    elements = []

    if company_lines:
        elements.append(Paragraph(" · ".join(company_lines), muted_style))
    elements.append(Spacer(1, 1 * cm))

    if customer_lines:
        elements.append(Paragraph("<br/>".join(customer_lines), styles["Normal"]))
    elements.append(Spacer(1, 1 * cm))

    elements.append(Paragraph(f"{doc_type_label} {document['doc_number']}", styles["Title"]))

    meta_parts = [f"Datum: {document.get('issue_date') or '-'}"]
    if document["doc_type"] == "angebot":
        meta_parts.append(f"Gültig bis: {document.get('valid_until') or '-'}")
    else:
        meta_parts.append(f"Zahlbar bis: {document.get('due_date') or '-'}")
    elements.append(Paragraph(" &nbsp;&nbsp;·&nbsp;&nbsp; ".join(meta_parts), muted_style))
    elements.append(Spacer(1, 0.7 * cm))

    header = ["Pos.", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "MwSt.", "Gesamt"]
    rows = [header]
    for i, item in enumerate(document.get("items", []), start=1):
        line_total = item["quantity"] * item["unit_price"]
        rows.append(
            [
                str(i),
                item["description"],
                f"{item['quantity']:g}",
                item.get("unit") or "-",
                _fmt_amount(item["unit_price"], currency),
                f"{item['tax_rate']:g}%",
                _fmt_amount(line_total, currency),
            ]
        )

    table = Table(
        rows,
        repeatRows=1,
        hAlign="LEFT",
        colWidths=[1.0 * cm, 5.5 * cm, 1.8 * cm, 1.7 * cm, 2.4 * cm, 1.3 * cm, 2.3 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_BG, _ALT_ROW_BG]),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    summary_rows = [
        ["Netto-Summe", _fmt_amount(document.get("net_total"), currency)],
        ["MwSt.", _fmt_amount(document.get("tax_total"), currency)],
        ["Gesamtbetrag", _fmt_amount(document.get("gross_total"), currency)],
    ]
    summary_table = Table(summary_rows, colWidths=[4 * cm, 3 * cm], hAlign="RIGHT")
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, _BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 1 * cm))

    if document.get("notes"):
        elements.append(Paragraph(document["notes"], styles["Normal"]))
        elements.append(Spacer(1, 0.5 * cm))

    if document["doc_type"] == "rechnung":
        bank_parts = []
        if company.get("bank_name"):
            bank_parts.append(f"Bank: {company['bank_name']}")
        if company.get("bank_iban"):
            bank_parts.append(f"IBAN: {company['bank_iban']}")
        if bank_parts:
            elements.append(Paragraph(" · ".join(bank_parts), muted_style))
    else:
        elements.append(
            Paragraph(
                "Dieses Angebot ist freibleibend und unverbindlich, sofern nicht "
                "anders angegeben.",
                muted_style,
            )
        )

    doc.build(elements)
    return buffer.getvalue()
