from __future__ import annotations

from pathlib import Path

from app.db import get_connection

_COLUMNS = ["name", "street", "zip_code", "city", "email", "phone"]


def init_customers_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                name TEXT NOT NULL,
                street TEXT,
                zip_code TEXT,
                city TEXT,
                email TEXT,
                phone TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_customer(data: dict, db_path: Path | None = None) -> int:
    conn = get_connection(db_path)
    try:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO customers ({columns}) VALUES ({placeholders})",
            {col: data.get(col) for col in _COLUMNS},
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_customers(db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_customer(customer_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_customer(customer_id: int, data: dict, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        assignments = ", ".join(f"{col} = :{col}" for col in _COLUMNS)
        params = {col: data.get(col) for col in _COLUMNS}
        params["id"] = customer_id
        cursor = conn.execute(
            f"UPDATE customers SET {assignments} WHERE id = :id", params
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_customer(customer_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
