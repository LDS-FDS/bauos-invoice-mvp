from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

_INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]')

_GERMAN_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

# Suppliers whose filing name deliberately differs from both the extracted
# legal name and the matched Vertragspartner folder name (e.g. an
# established lowercase spelling in past filings). Keyed by the lowercased
# extracted supplier name.
_SUPPLIER_NAME_OVERRIDES: dict[str, str] = {
    "wego systembaustoffe gmbh": "wego",
    "possling gmbh & co.kg": "Holz Possling",
}


def _sanitize_filename_part(value: str) -> str:
    return _INVALID_FILENAME_CHARS_RE.sub("-", value).strip()


def _german_month_name(month: int) -> str:
    return _GERMAN_MONTHS[month - 1]


def _invoice_date_parts(invoice: dict) -> tuple[int, int, int]:
    raw = invoice.get("invoice_date")
    if raw:
        try:
            parsed = datetime.strptime(raw, "%d.%m.%Y")
            return parsed.year, parsed.month, parsed.day
        except ValueError:
            pass

    created_at = invoice.get("created_at")
    if created_at:
        try:
            parsed = datetime.strptime(created_at[:10], "%Y-%m-%d")
            return parsed.year, parsed.month, parsed.day
        except ValueError:
            pass

    now = datetime.now()
    return now.year, now.month, now.day


def build_invoice_filename(invoice: dict, supplier_override: str | None = None) -> str:
    year, month, day = _invoice_date_parts(invoice)
    date_part = f"{year % 100:02d}{month:02d}{day:02d}"

    supplier = _sanitize_filename_part(supplier_override or invoice.get("supplier") or "Unbekannt")
    invoice_number = _sanitize_filename_part(
        str(invoice.get("invoice_number") or invoice.get("id") or "unbekannt")
    )
    doc_label = "GUS" if invoice.get("is_gutschrift") else "INV"

    return f"{date_part} {doc_label} {supplier} RE-NR. {invoice_number}.pdf"


def _supplier_name_override(supplier: str) -> str | None:
    return _SUPPLIER_NAME_OVERRIDES.get(supplier.strip().lower())


def _resolve_supplier_folder_name(supplier: str, base_path: str) -> str:
    """Reuse an existing Vertragspartner folder if the supplier name contains it
    (e.g. "Wego Systembaustoffe GmbH" -> existing folder "Wego"), instead of
    creating a new folder from the full legal name every time. For suppliers
    whose extracted name doesn't share a substring with their real folder at
    all (e.g. "Possling GmbH & Co.KG" -> existing folder "Holz Possling"),
    fall back to the explicit override table."""
    sanitized = _sanitize_filename_part(supplier)
    override = _supplier_name_override(supplier)
    vertragspartner_dir = Path(base_path) / "03 Vertragspartner"
    try:
        existing_folders = [p.name for p in vertragspartner_dir.iterdir() if p.is_dir()]
    except OSError:
        return override or sanitized

    if override:
        for name in existing_folders:
            if name.lower() == override.lower():
                return name

    matches = [name for name in existing_folders if name.lower() in sanitized.lower()]
    if matches:
        return max(matches, key=len)
    return override or sanitized


def file_paid_invoice(invoice: dict, base_path: str | None) -> list[str]:
    source = invoice.get("file_path")
    if not base_path or not source or not os.path.isfile(source):
        return []

    raw_supplier = invoice.get("supplier") or "Unbekannt"
    folder_name = _resolve_supplier_folder_name(raw_supplier, base_path)
    filename_supplier = _supplier_name_override(raw_supplier) or folder_name
    filename = build_invoice_filename(invoice, supplier_override=filename_supplier)
    year, month, _ = _invoice_date_parts(invoice)
    month_folder = f"{month:02d} {_german_month_name(month)} {year}"

    base = Path(base_path)
    targets = [
        base / "03 Vertragspartner" / folder_name / filename,
        base / "09 FIBU" / str(year) / month_folder / "01 Eingang" / filename,
        base / "09 FIBU" / str(year) / month_folder / "02 für Datev" / filename,
    ]

    written = []
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            written.append(str(target))
        except OSError:
            continue
    return written
