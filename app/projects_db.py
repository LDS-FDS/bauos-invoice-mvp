from __future__ import annotations

from pathlib import Path

from app.db import get_connection

_COLUMNS = [
    "name",
    "customer_id",
    "street",
    "zip_code",
    "city",
    "status",
    "start_date",
    "end_date",
    "notes",
]


def init_projects_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                name TEXT NOT NULL,
                customer_id INTEGER REFERENCES customers(id),
                street TEXT,
                zip_code TEXT,
                city TEXT,
                status TEXT NOT NULL DEFAULT 'aktiv',
                start_date TEXT,
                end_date TEXT,
                notes TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_project(data: dict, db_path: Path | None = None) -> int:
    conn = get_connection(db_path)
    try:
        payload = {col: data.get(col) for col in _COLUMNS}
        payload["status"] = payload.get("status") or "aktiv"
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO projects ({columns}) VALUES ({placeholders})", payload
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_projects(db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT projects.*, customers.name AS customer_name
            FROM projects
            LEFT JOIN customers ON customers.id = projects.customer_id
            ORDER BY projects.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_project(project_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT projects.*, customers.name AS customer_name
            FROM projects
            LEFT JOIN customers ON customers.id = projects.customer_id
            WHERE projects.id = ?
            """,
            (project_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_project(project_id: int, data: dict, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        assignments = ", ".join(f"{col} = :{col}" for col in _COLUMNS)
        params = {col: data.get(col) for col in _COLUMNS}
        params["id"] = project_id
        cursor = conn.execute(
            f"UPDATE projects SET {assignments} WHERE id = :id", params
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_project(project_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE invoices SET project_id = NULL WHERE project_id = ?", (project_id,)
        )
        conn.execute(
            "UPDATE documents SET project_id = NULL WHERE project_id = ?", (project_id,)
        )
        conn.execute("DELETE FROM time_entries WHERE project_id = ?", (project_id,))
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
