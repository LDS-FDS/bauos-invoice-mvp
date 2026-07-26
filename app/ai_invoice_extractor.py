from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

MODEL = "claude-opus-5"

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier": {"type": ["string", "null"]},
        "invoice_number": {"type": ["string", "null"]},
        "invoice_date": {
            "type": ["string", "null"],
            "description": "Format DD.MM.YYYY if stated",
        },
        "total_amount": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "due_date": {
            "type": ["string", "null"],
            "description": "Format DD.MM.YYYY if a due date is stated",
        },
        "skonto_percent": {"type": ["number", "null"]},
        "skonto_date": {
            "type": ["string", "null"],
            "description": "Format DD.MM.YYYY - the earlier due date if Skonto is paid within it",
        },
        "bank_account": {
            "type": ["string", "null"],
            "description": "IBAN or other bank account identifier the invoice should be paid to",
        },
    },
    "required": [
        "supplier",
        "invoice_number",
        "invoice_date",
        "total_amount",
        "currency",
        "due_date",
        "skonto_percent",
        "skonto_date",
        "bank_account",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You extract structured data from German construction-industry invoices, "
    "including ones with unusual layout or wording that a regex parser would miss. "
    "Read the raw invoice text and extract: supplier name, invoice number, invoice date, "
    "total amount, currency, payment due date, and Skonto (early-payment discount) "
    "percent/date, plus the bank account (IBAN) the invoice should be paid to. "
    "Use null for anything not stated in the text. "
    "Never guess or infer a value that isn't actually written in the invoice."
)


class InvoiceExtractionRefused(RuntimeError):
    pass


@dataclass
class AIInvoiceData:
    supplier: str | None
    invoice_number: str | None
    invoice_date: str | None
    total_amount: float | None
    currency: str | None
    due_date: str | None
    skonto_percent: float | None
    skonto_date: str | None
    bank_account: str | None


def extract_invoice_with_ai(
    text: str, client: anthropic.Anthropic | None = None
) -> AIInvoiceData:
    client = client or anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": INVOICE_SCHEMA}},
    )

    if response.stop_reason == "refusal":
        raise InvoiceExtractionRefused("AI extraction was declined by safety classifiers")

    result_text = next(block.text for block in response.content if block.type == "text")
    data = json.loads(result_text)
    return AIInvoiceData(**data)
