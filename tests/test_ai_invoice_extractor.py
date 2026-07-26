import json
from unittest.mock import MagicMock

import pytest

from app.ai_invoice_extractor import InvoiceExtractionRefused, extract_invoice_with_ai

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
        "total_amount": 980.50,
        "currency": "EUR",
        "due_date": None,
        "payment_term_days": None,
        "skonto_percent": 3.0,
        "skonto_date": None,
        "skonto_days": None,
    }
    client = _mock_client(payload)

    result = extract_invoice_with_ai(UNSTRUCTURED_INVOICE, client=client)

    assert result.supplier == "Handwerksbetrieb Schmidt"
    assert result.total_amount == 980.50
    assert result.skonto_percent == 3.0
    client.messages.create.assert_called_once()


def test_raises_on_refusal():
    client = _mock_client({}, stop_reason="refusal")

    with pytest.raises(InvoiceExtractionRefused):
        extract_invoice_with_ai(UNSTRUCTURED_INVOICE, client=client)
