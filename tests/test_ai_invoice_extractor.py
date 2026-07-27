import json
from unittest.mock import MagicMock

import pytest

from app.ai_invoice_extractor import (
    InvoiceExtractionRefused,
    extract_invoice_from_image,
    extract_invoice_with_ai,
)

UNSTRUCTURED_INVOICE = """
Handwerksbetrieb Schmidt
Rechnung für geleistete Arbeiten im Juli, insgesamt 980,50 EUR fällig.
Bitte bis Ende des Monats überweisen, bei schneller Zahlung 3% Nachlass.
"""


def _mock_client(payload: dict, stop_reason: str = "end_turn") -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.stop_reason = stop_reason
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload)
    response.content = [text_block]
    client.messages.create.return_value = response
    return client


def test_extracts_fields_from_ai_response():
    payload = {
        "supplier": "Handwerksbetrieb Schmidt",
        "invoice_number": None,
        "invoice_date": None,
        "total_amount": 980.50,
        "currency": "EUR",
        "due_date": None,
        "skonto_percent": 3.0,
        "skonto_date": None,
        "skonto_amount": None,
        "bank_account": None,
        "bank_name": None,
    }
    client = _mock_client(payload)

    result = extract_invoice_with_ai(UNSTRUCTURED_INVOICE, client=client)

    assert result.supplier == "Handwerksbetrieb Schmidt"
    assert result.total_amount == 980.50
    assert result.skonto_percent == 3.0
    client.messages.create.assert_called_once()


def test_raises_on_refusal():
    client = _mock_client(
        {
            "supplier": None,
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
            "currency": None,
            "due_date": None,
            "skonto_percent": None,
            "skonto_date": None,
            "skonto_amount": None,
            "bank_account": None,
            "bank_name": None,
        },
        stop_reason="refusal",
    )

    with pytest.raises(InvoiceExtractionRefused):
        extract_invoice_with_ai(UNSTRUCTURED_INVOICE, client=client)


def test_extracts_fields_from_scanned_image():
    payload = {
        "supplier": "Dreiling Aufzugbau GmbH",
        "invoice_number": "20252313",
        "invoice_date": None,
        "total_amount": 1234.56,
        "currency": "EUR",
        "due_date": None,
        "skonto_percent": None,
        "skonto_date": None,
        "skonto_amount": None,
        "bank_account": None,
        "bank_name": None,
    }
    client = _mock_client(payload)

    result = extract_invoice_from_image(b"fake-png-bytes", client=client)

    assert result.supplier == "Dreiling Aufzugbau GmbH"
    assert result.total_amount == 1234.56
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["messages"][0]["content"][0]["type"] == "image"
    assert call_kwargs["messages"][0]["content"][0]["source"]["media_type"] == "image/png"


def test_image_extraction_raises_on_refusal():
    client = _mock_client(
        {
            "supplier": None,
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
            "currency": None,
            "due_date": None,
            "skonto_percent": None,
            "skonto_date": None,
            "skonto_amount": None,
            "bank_account": None,
            "bank_name": None,
        },
        stop_reason="refusal",
    )

    with pytest.raises(InvoiceExtractionRefused):
        extract_invoice_from_image(b"fake-png-bytes", client=client)
