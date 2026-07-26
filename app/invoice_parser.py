from __future__ import annotations

import re
from dataclasses import dataclass

_LEGAL_FORM_RE = re.compile(
    r"^.{0,80}\b(GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|OHG|UG|e\.\s?K\.)\b.{0,40}$"
)

_AMOUNT_LABEL_RE = re.compile(
    r"(?:Gesamtbetrag|Rechnungsbetrag|Endbetrag|Bruttobetrag)"
    r"[^\d\n]{0,20}([\d.]+,\d{2})\s*(EUR|€)?",
    re.IGNORECASE,
)

_DUE_DATE_RE = re.compile(
    r"(?:Zahlbar\s+bis|F[äa]llig\s+am|Zahlungsziel)\D{0,10}(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_PAYMENT_TERM_DAYS_RE = re.compile(
    r"Zahlungsziel\D{0,10}(\d{1,3})\s*Tage",
    re.IGNORECASE,
)

_SKONTO_RE = re.compile(
    r"(\d{1,2}(?:,\d+)?)\s*%\s*Skonto"
    r"(?:[^\d\n]{0,30}(\d{1,2}\.\d{1,2}\.\d{2,4})"
    r"|[^\d\n]{0,20}innerhalb\D{0,5}(\d{1,3})\s*Tagen)?",
    re.IGNORECASE,
)


@dataclass
class InvoiceData:
    supplier: str | None
    total_amount: float | None
    currency: str | None
    due_date: str | None
    payment_term_days: int | None
    skonto_percent: float | None
    skonto_date: str | None
    skonto_days: int | None


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
    lines = [line for line in text.splitlines()]

    supplier = _extract_supplier(lines)

    total_amount = None
    currency = None
    if match := _AMOUNT_LABEL_RE.search(text):
        total_amount = _parse_german_amount(match.group(1))
        currency = match.group(2) or "EUR"

    due_date = None
    if match := _DUE_DATE_RE.search(text):
        due_date = match.group(1)

    payment_term_days = None
    if match := _PAYMENT_TERM_DAYS_RE.search(text):
        payment_term_days = int(match.group(1))

    skonto_percent = None
    skonto_date = None
    skonto_days = None
    if match := _SKONTO_RE.search(text):
        skonto_percent = float(match.group(1).replace(",", "."))
        skonto_date = match.group(2)
        skonto_days = int(match.group(3)) if match.group(3) else None

    return InvoiceData(
        supplier=supplier,
        total_amount=total_amount,
        currency=currency,
        due_date=due_date,
        payment_term_days=payment_term_days,
        skonto_percent=skonto_percent,
        skonto_date=skonto_date,
        skonto_days=skonto_days,
    )
