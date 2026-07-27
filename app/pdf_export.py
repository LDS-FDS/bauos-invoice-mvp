from __future__ import annotations

import io
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_HEADER_BG = colors.HexColor("#6fb0c2")
_ROW_BG = colors.HexColor("#fffdf8")
_ALT_ROW_BG = colors.HexColor("#f4ede1")
_BORDER = colors.HexColor("#e6dcc9")


def _format_amount(invoice: dict) -> str:
    if invoice.get("total_amount") is None:
        return "-"
    currency = invoice.get("currency") or ""
    return f"{invoice['total_amount']:.2f} {currency}".strip()


def build_invoice_list_pdf(invoices: Sequence[dict]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title="Rechnungsübersicht",
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("BauOS – Rechnungsübersicht", styles["Title"]),
        Spacer(1, 0.5 * cm),
    ]

    header = ["Nr.", "Lieferant", "Betrag", "Zahlbar bis", "Skonto bis", "Status"]
    rows = [header]
    for invoice in invoices:
        rows.append(
            [
                invoice.get("invoice_number") or "-",
                invoice.get("supplier") or "-",
                _format_amount(invoice),
                invoice.get("due_date") or "-",
                invoice.get("skonto_date") or "-",
                invoice.get("status") or "-",
            ]
        )

    if len(rows) == 1:
        elements.append(Paragraph("Keine Rechnungen vorhanden.", styles["Normal"]))
    else:
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_BG, _ALT_ROW_BG]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)

    doc.build(elements)
    return buffer.getvalue()
