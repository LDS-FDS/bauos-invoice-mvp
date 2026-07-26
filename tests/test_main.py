from app.invoice_parser import InvoiceData
from app.main import _build_response


def test_build_response_computes_amount_with_skonto():
    data = InvoiceData(
        supplier="Mustermann Bau GmbH",
        invoice_number="2026-045",
        invoice_date="01.07.2026",
        total_amount=4250.00,
        currency="EUR",
        due_date="31.07.2026",
        skonto_percent=2.0,
        skonto_date="10.07.2026",
        bank_account="DE89370400440532013000",
    )

    response = _build_response(data)

    assert response["amount_with_skonto"] == 4165.00


def test_build_response_without_skonto_has_no_amount_with_skonto():
    data = InvoiceData(
        supplier="Mustermann Bau GmbH",
        invoice_number=None,
        invoice_date=None,
        total_amount=1000.00,
        currency="EUR",
        due_date=None,
        skonto_percent=None,
        skonto_date=None,
        bank_account=None,
    )

    response = _build_response(data)

    assert response["amount_with_skonto"] is None
