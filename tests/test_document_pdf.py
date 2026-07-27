from app.document_pdf import build_document_pdf

COMPANY = {
    "name": "CIDE Concept GmbH",
    "street": "Knesebeckstr. 62",
    "zip_code": "10719",
    "city": "Berlin",
    "bank_name": "Musterbank",
    "bank_iban": "DE89370400440532013000",
}

DOCUMENT = {
    "doc_type": "rechnung",
    "doc_number": "RE-2026-001",
    "issue_date": "27.07.2026",
    "due_date": "10.08.2026",
    "notes": "Vielen Dank für den Auftrag.",
    "net_total": 570.0,
    "tax_total": 108.3,
    "gross_total": 678.3,
    "customer": {
        "name": "Muster Immobilien GmbH",
        "street": "Musterstraße 1",
        "zip_code": "10719",
        "city": "Berlin",
    },
    "items": [
        {"description": "Trockenbauarbeiten", "quantity": 10, "unit": "Std.", "unit_price": 45.0, "tax_rate": 19.0},
        {"description": "Material", "quantity": 1, "unit": "Pauschal", "unit_price": 120.0, "tax_rate": 19.0},
    ],
}


def test_build_document_pdf_returns_valid_pdf_bytes():
    pdf_bytes = build_document_pdf(DOCUMENT, COMPANY)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_document_pdf_for_angebot():
    angebot = {**DOCUMENT, "doc_type": "angebot", "doc_number": "ANG-2026-001", "valid_until": "15.08.2026"}
    pdf_bytes = build_document_pdf(angebot, COMPANY)
    assert pdf_bytes.startswith(b"%PDF")


def test_build_document_pdf_without_notes_or_customer():
    minimal = {**DOCUMENT, "notes": None, "customer": None}
    pdf_bytes = build_document_pdf(minimal, COMPANY)
    assert pdf_bytes.startswith(b"%PDF")
