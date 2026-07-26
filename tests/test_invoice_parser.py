from app.invoice_parser import parse_invoice_text

SAMPLE_INVOICE = """
Mustermann Bau GmbH
Musterstraße 1
12345 Musterstadt

Rechnung Nr. 2026-045
Datum: 01.07.2026

Leistung: Trockenbauarbeiten Projekt "Wohnhaus Nord"

Gesamtbetrag: 4.250,00 EUR

Zahlungsziel: 30 Tage netto
Zahlbar bis 31.07.2026
2% Skonto bei Zahlung bis 10.07.2026
"""


def test_extracts_supplier():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.supplier == "Mustermann Bau GmbH"


def test_extracts_total_amount_and_currency():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.total_amount == 4250.00
    assert result.currency == "EUR"


def test_extracts_due_date():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.due_date == "31.07.2026"


def test_extracts_payment_term_days():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.payment_term_days == 30


def test_extracts_skonto():
    result = parse_invoice_text(SAMPLE_INVOICE)
    assert result.skonto_percent == 2.0
    assert result.skonto_date == "10.07.2026"


def test_missing_fields_are_none():
    result = parse_invoice_text("Ein Text ganz ohne Rechnungsdaten.")
    assert result.total_amount is None
    assert result.due_date is None
    assert result.skonto_percent is None
