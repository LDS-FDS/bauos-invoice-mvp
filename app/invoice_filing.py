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


def build_invoice_filename(invoice: dict) -> str:
    year, month, day = _invoice_date_parts(invoice)
    date_part = f"{year % 100:02d}{month:02d}{day:02d}"

    supplier = _sanitize_filename_part(invoice.get("supplier") or "Unbekannt")
    invoice_number = _sanitize_filename_part(
        str(invoice.get("invoice_number") or invoice.get("id") or "unbekannt")
    )

    return f"{date_part} INV {supplier} RE-NR. {invoice_number}.pdf"


def file_paid_invoice(invoice: dict, base_path: str | None) -> list[str]:
    source = invoice.get("file_path")
    if not base_path or not source or not os.path.isfile(source):
        return []

    filename = build_invoice_filename(invoice)
    year, month, _ = _invoice_date_parts(invoice)
    month_folder = f"{month:02d} {_german_month_name(month)} {year}"
    supplier = _sanitize_filename_part(invoice.get("supplier") or "Unbekannt")

    base = Path(base_path)
    targets = [
        base / "03 Vertragspartner" / supplier / filename,
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
