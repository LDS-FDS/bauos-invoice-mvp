from __future__ import annotations

from pathlib import Path

from app.db import get_connection

_COLUMNS = ["name", "hourly_rate"]


def init_employees_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                name TEXT NOT NULL,
                hourly_rate REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_employee(data: dict, db_path: Path | None = None) -> int:
    conn = get_connection(db_path)
    try:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO employees ({columns}) VALUES ({placeholders})",
            {col: data.get(col) for col in _COLUMNS},
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_employees(db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM employees ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_employee(employee_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_employee(employee_id: int, data: dict, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        assignments = ", ".join(f"{col} = :{col}" for col in _COLUMNS)
        params = {col: data.get(col) for col in _COLUMNS}
        params["id"] = employee_id
        cursor = conn.execute(
            f"UPDATE employees SET {assignments} WHERE id = :id", params
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_employee(employee_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM time_entries WHERE employee_id = ?", (employee_id,))
        cursor = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
