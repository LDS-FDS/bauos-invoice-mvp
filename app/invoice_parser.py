from __future__ import annotations

import re
from dataclasses import dataclass

_LEGAL_FORM_RE = re.compile(
    r"^.{0,80}\b(GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|OHG|UG|e\.\s?K\.)\b.{0,40}$"
)

_INVOICE_NUMBER_RE = re.compile(
    r"Rechnung(?:s?nummer|\s*Nr\.?)\s*[:.]?\s*([A-Za-z0-9\-/]+)",
    re.IGNORECASE,
)

_INVOICE_DATE_RE = re.compile(
    r"(?:Rechnungsdatum|Datum)\s*[:.]?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_AMOUNT_LABEL_RE = re.compile(
    r"(?:Gesamtbetrag|Rechnungsbetrag|Endbetrag|Bruttobetrag)"
    r"[^\d\n]{0,20}([\d.]+,\d{2})\s*(EUR|€)?",
    re.IGNORECASE,
)

_DUE_DATE_RE = re.compile(
    r"(?:Zahlbar\s+bis|F[äa]llig\s+am)\D{0,10}(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_SKONTO_RE = re.compile(
    r"(\d{1,2}(?:,\d+)?)\s*%\s*Skonto(?:[^\d\n]{0,30}(\d{1,2}\.\d{1,2}\.\d{2,4}))?",
    re.IGNORECASE,
)

_IBAN_RE = re.compile(
    r"IBAN\s*[:.]?\s*([A-Z]{2}[0-9A-Z ]{13,32})",
    re.IGNORECASE,
)


@dataclass
class InvoiceData:
    supplier: str | None
    invoice_number: str | None
    invoice_date: str | None
    total_amount: float | None
    currency: str | None
    due_date: str | None
    skonto_percent: float | None
    skonto_date: str | None
    bank_account: str | None


def _parse_german_amount(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def _extract_supplier(lines: list[str]) -> str | None:
    for line in lines[:15]:
        if _LEGAL_FORM_RE.match(line.strip()):
            return line.strip()
    for line in lines:
        if line.strip():
            return line.strip()
    return None


def parse_invoice_text(text: str) -> InvoiceData:
    lines = text.splitlines()

    supplier = _extract_supplier(lines)

    invoice_number = None
    if match := _INVOICE_NUMBER_RE.search(text):
        invoice_number = match.group(1)

    invoice_date = None
    if match := _INVOICE_DATE_RE.search(text):
        invoice_date = match.group(1)

    total_amount = None
    currency = None
    if match := _AMOUNT_LABEL_RE.search(text):
        total_amount = _parse_german_amount(match.group(1))
        currency = match.group(2) or "EUR"

    due_date = None
    if match := _DUE_DATE_RE.search(text):
        due_date = match.group(1)

    skonto_percent = None
    skonto_date = None
    if match := _SKONTO_RE.search(text):
        skonto_percent = float(match.group(1).replace(",", "."))
        skonto_date = match.group(2)

    bank_account = None
    if match := _IBAN_RE.search(text):
        bank_account = match.group(1).replace(" ", "").upper()

    return InvoiceData(
        supplier=supplier,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
        currency=currency,
        due_date=due_date,
        skonto_percent=skonto_percent,
        skonto_date=skonto_date,
        bank_account=bank_account,
    )
