from app.pdf_export import build_invoice_list_pdf

SAMPLE_INVOICES = [
    {
        "invoice_number": "2026-045",
        "supplier": "Mustermann Bau GmbH",
        "total_amount": 4250.00,
        "currency": "EUR",
        "due_date": "31.07.2026",
        "skonto_date": "10.07.2026",
        "status": "offen",
    },
    {
        "invoice_number": "2026-046",
        "supplier": "Beispiel Baustoffe GmbH",
        "total_amount": 100.0,
        "currency": "EUR",
        "due_date": "01.08.2026",
        "skonto_date": None,
        "status": "bezahlt",
    },
]


def test_build_invoice_list_pdf_returns_valid_pdf_bytes():
    pdf_bytes = build_invoice_list_pdf(SAMPLE_INVOICES)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_invoice_list_pdf_handles_empty_list():
    pdf_bytes = build_invoice_list_pdf([])
    assert pdf_bytes.startswith(b"%PDF")
