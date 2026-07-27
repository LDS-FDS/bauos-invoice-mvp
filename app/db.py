from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "bauos.db"

_COLUMNS = [
    "supplier",
    "invoice_number",
    "invoice_date",
    "total_amount",
    "currency",
    "due_date",
    "skonto_percent",
    "skonto_date",
    "amount_with_skonto",
    "bank_account",
    "bank_name",
]


def _resolve_path(db_path: Path | None) -> Path:
    return db_path if db_path is not None else DEFAULT_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                supplier TEXT,
                invoice_number TEXT,
                invoice_date TEXT,
                total_amount REAL,
                currency TEXT,
                due_date TEXT,
                skonto_percent REAL,
                skonto_date TEXT,
                amount_with_skonto REAL,
                bank_account TEXT,
                bank_name TEXT,
                status TEXT NOT NULL DEFAULT 'offen'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_invoice(data: dict, db_path: Path | None = None) -> int:
    conn = get_connection(db_path)
    try:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO invoices ({columns}) VALUES ({placeholders})",
            {col: data.get(col) for col in _COLUMNS},
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_invoices(db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_invoice(invoice_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_status(invoice_id: int, status: str, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_invoice(invoice_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
