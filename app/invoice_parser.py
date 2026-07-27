from __future__ import annotations

import re
from dataclasses import dataclass

_LEGAL_FORM_RE = re.compile(
    r"^(.{0,80}?\b(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|OHG|UG|e\.\s?K\.))\b"
)

_INVOICE_NUMBER_LABELED_RE = re.compile(
    r"(?:Rechnung(?:s?nummer|\s*Nr\.?)|Beleg-?\s*Nr\.?)\s*[:.]?\s*([A-Za-z0-9\-/]+)",
    re.IGNORECASE,
)

_INVOICE_NUMBER_VOM_RE = re.compile(
    r"Rechnung\s+([A-Za-z0-9\-/]+)\s+vom\s+(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_INVOICE_NUMBER_BARE_RE = re.compile(
    r"^Rechnung\s+([A-Za-z0-9\-/]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_INVOICE_DATE_RE = re.compile(
    r"(?:Rechnungsdatum|Datum)\s*[:.]?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_AMOUNT_LABEL_RE = re.compile(
    r"(?:Gesamtbetrag|Rechnungsbetrag|Endbetrag|Bruttobetrag)"
    r"[^\d\n]{0,20}(\d[\d. ]*,\d{2})\s*(EUR|€)?",
    re.IGNORECASE,
)

_DUE_DATE_RE = re.compile(
    r"(?:Zahlbar\s+bis|F[äa]llig\s+am)\D{0,10}(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_DUE_DATE_OHNE_ABZUG_RE = re.compile(
    r"Bis\s+zum\s+(\d{1,2}\.\d{1,2}\.\d{2,4})\s+ohne\s+Abzug",
    re.IGNORECASE,
)

_SKONTO_RE = re.compile(
    r"(\d{1,2}(?:,\d+)?)\s*%\s*Skonto(?:[^\d\n]{0,30}(\d{1,2}\.\d{1,2}\.\d{2,4}))?",
    re.IGNORECASE,
)

_SKONTO_BIS_ZUM_RE = re.compile(
    r"Bis\s+zum\s+(\d{1,2}\.\d{1,2}\.\d{2,4})\s+erhalten\s+Sie\s+(\d{1,3}(?:,\d+)?)\s*%\s*Skonto"
    r"(?:[^\d\n]{0,20}(\d[\d. ]*,\d{2}))?",
    re.IGNORECASE,
)

_SKONTO_LASTSCHRIFT_DATE_RE = re.compile(
    r"Lastschrift\s+am\s+(\d{1,2}\.\d{1,2}\.\d{2,4})",
    re.IGNORECASE,
)

_IBAN_LABELED_RE = re.compile(
    r"IBAN\s*[:.]?\s*([A-Z]{2}[0-9A-Z ]{13,32})",
    re.IGNORECASE,
)

_IBAN_BARE_RE = re.compile(r"\bDE\d{2}(?:\s?\d{4}){4}\s?\d{2}\b")

_BANK_NAME_RE = re.compile(
    r"\b((?:\w*bank\b|sparkasse\b)(?:\s+[A-ZÄÖÜ&][\wÄÖÜäöüß.]*){0,2})",
    re.IGNORECASE,
)

_AMOUNT_TOKEN_RE = re.compile(r"^\d[\d.]*,\d{2}$")

_AMOUNT_GEGEBEN_RE = re.compile(
    r"Gegeben\s*:?\s*(?:[A-Za-zÄÖÜäöüß\-]+\s+)?(\d[\d. ]*,\d{2})\s*(EUR|€)?",
    re.IGNORECASE,
)

_CUSTOMER_LABELS = {"firma", "kunde", "kundenname", "empfänger", "rechnungsadresse", "lieferadresse"}
_DOC_TITLE_WORDS = {"rechnung", "angebot", "lieferschein", "beleg", "auftrag", "auftragsbestätigung"}
_DOC_TITLE_RE = re.compile(r"^(rechnung|angebot|lieferschein|beleg)\s+[\w\-/]+$", re.IGNORECASE)

_EMAIL_DOMAIN_RE = re.compile(r"[\w.+-]+@([\w-]+)\.(?:de|com|net|org|eu)", re.IGNORECASE)
_GENERIC_EMAIL_DOMAINS = {
    "gmail", "gmx", "web", "t-online", "outlook", "yahoo", "hotmail", "icloud",
}


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
    skonto_amount: float | None
    bank_account: str | None
    bank_name: str | None


def _parse_german_amount(raw: str) -> float:
    return float(raw.replace(" ", "").replace(".", "").replace(",", "."))


def _guess_supplier_from_email(text: str) -> str | None:
    for match in _EMAIL_DOMAIN_RE.finditer(text):
        domain = match.group(1).lower()
        if domain in _GENERIC_EMAIL_DOMAINS:
            continue
        return " ".join(word.capitalize() for word in domain.split("-"))
    return None


def _is_doc_title(stripped: str) -> bool:
    normalized = stripped.lower().rstrip(":")
    return normalized in _DOC_TITLE_WORDS or bool(_DOC_TITLE_RE.match(normalized))


def _is_customer_label(stripped: str) -> bool:
    return stripped.lower().rstrip(":") in _CUSTOMER_LABELS


def _extract_supplier(lines: list[str], text: str) -> str | None:
    non_empty = [line.strip() for line in lines if line.strip()]

    prev = ""
    for stripped in non_empty[:15]:
        preceded_by_customer_label = _is_customer_label(prev)
        prev = stripped
        if preceded_by_customer_label or _is_doc_title(stripped) or _is_customer_label(stripped):
            continue
        if match := _LEGAL_FORM_RE.match(stripped):
            return match.group(1).strip()

    # No legal-form match nearby (e.g. supplier name is only in a logo image).
    # Only trust the very first substantive line as a plain company name -
    # further down we're increasingly likely to be reading customer/address
    # details rather than the sender.
    prev = ""
    for stripped in non_empty[:3]:
        preceded_by_customer_label = _is_customer_label(prev)
        prev = stripped
        if preceded_by_customer_label or _is_doc_title(stripped) or _is_customer_label(stripped):
            continue
        return stripped

    # Last resort: the supplier's name is sometimes only present in a logo
    # image, but a staff email address (e.g. sachbearbeiter@supplier.de)
    # usually still is - use its domain as a readable approximation.
    return _guess_supplier_from_email(text)


def _extract_amount_from_endbetrag_table(lines: list[str]) -> tuple[float | None, str | None]:
    for i, line in enumerate(lines):
        if re.search(r"\bEndbetrag\b", line, re.IGNORECASE):
            for candidate_line in lines[i + 1 : i + 3]:
                tokens = [t for t in candidate_line.split() if _AMOUNT_TOKEN_RE.match(t)]
                if tokens:
                    return _parse_german_amount(tokens[-1]), "EUR"
    return None, None


def _extract_bank_name(lines: list[str], bank_account: str | None) -> str | None:
    if bank_account is None:
        return None
    for i, line in enumerate(lines):
        cleaned = re.sub(r"\s+", "", line).upper()
        if bank_account in cleaned:
            # The bank name isn't always on the same line as the IBAN (e.g.
            # "Bankverbindung: Commerzbank AG" on the line above) - check a
            # small window ending at the IBAN's own line, closest match first.
            for candidate_line in reversed(lines[max(0, i - 2) : i + 1]):
                if match := _BANK_NAME_RE.search(candidate_line):
                    return match.group(1).strip()
    return None


def _extract_invoice_number_and_date(text: str) -> tuple[str | None, str | None]:
    invoice_number = None
    invoice_date = None

    if match := _INVOICE_NUMBER_LABELED_RE.search(text):
        invoice_number = match.group(1)

    if match := _INVOICE_DATE_RE.search(text):
        invoice_date = match.group(1)

    if invoice_number is None or invoice_date is None:
        if match := _INVOICE_NUMBER_VOM_RE.search(text):
            invoice_number = invoice_number or match.group(1)
            invoice_date = invoice_date or match.group(2)

    if invoice_number is None:
        if match := _INVOICE_NUMBER_BARE_RE.search(text):
            invoice_number = match.group(1)

    return invoice_number, invoice_date


def parse_invoice_text(text: str) -> InvoiceData:
    lines = text.splitlines()

    supplier = _extract_supplier(lines, text)
    invoice_number, invoice_date = _extract_invoice_number_and_date(text)

    total_amount = None
    currency = None
    if match := _AMOUNT_LABEL_RE.search(text):
        total_amount = _parse_german_amount(match.group(1))
        currency = match.group(2) or "EUR"
    if total_amount is None:
        total_amount, currency = _extract_amount_from_endbetrag_table(lines)
    if total_amount is None:
        if match := _AMOUNT_GEGEBEN_RE.search(text):
            total_amount = _parse_german_amount(match.group(1))
            currency = match.group(2) or "EUR"

    due_date = None
    if match := _DUE_DATE_RE.search(text):
        due_date = match.group(1)
    if due_date is None:
        if match := _DUE_DATE_OHNE_ABZUG_RE.search(text):
            due_date = match.group(1)

    skonto_percent = None
    skonto_date = None
    skonto_amount = None
    if match := _SKONTO_BIS_ZUM_RE.search(text):
        skonto_date = match.group(1)
        skonto_percent = float(match.group(2).replace(",", "."))
        if match.group(3):
            skonto_amount = _parse_german_amount(match.group(3))
    elif match := _SKONTO_RE.search(text):
        skonto_percent = float(match.group(1).replace(",", "."))
        skonto_date = match.group(2)

    if skonto_percent is not None and skonto_date is None:
        if match := _SKONTO_LASTSCHRIFT_DATE_RE.search(text):
            skonto_date = match.group(1)

    bank_account = None
    if match := _IBAN_LABELED_RE.search(text):
        bank_account = match.group(1).replace(" ", "").upper()
    elif match := _IBAN_BARE_RE.search(text):
        bank_account = match.group(0).replace(" ", "").upper()

    bank_name = _extract_bank_name(lines, bank_account)

    return InvoiceData(
        supplier=supplier,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_amount=total_amount,
        currency=currency,
        due_date=due_date,
        skonto_percent=skonto_percent,
        skonto_date=skonto_date,
        skonto_amount=skonto_amount,
        bank_account=bank_account,
        bank_name=bank_name,
    )
