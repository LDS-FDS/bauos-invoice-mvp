from __future__ import annotations

from pathlib import Path

from app.db import get_connection

_COLUMNS = [
    "name",
    "street",
    "zip_code",
    "city",
    "email",
    "phone",
    "tax_id",
    "bank_name",
    "bank_iban",
]


def init_company_settings_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS company_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT,
                street TEXT,
                zip_code TEXT,
                city TEXT,
                email TEXT,
                phone TEXT,
                tax_id TEXT,
                bank_name TEXT,
                bank_iban TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_company_settings(db_path: Path | None = None) -> dict:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
        if row:
            return dict(row)
        return {"id": 1, **{col: None for col in _COLUMNS}}
    finally:
        conn.close()


def save_company_settings(data: dict, db_path: Path | None = None) -> dict:
    conn = get_connection(db_path)
    try:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        updates = ", ".join(f"{col} = excluded.{col}" for col in _COLUMNS)
        conn.execute(
            f"""
            INSERT INTO company_settings (id, {columns}) VALUES (1, {placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
            """,
            {col: data.get(col) for col in _COLUMNS},
        )
        conn.commit()
    finally:
        conn.close()
    return get_company_settings(db_path)
