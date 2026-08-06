from __future__ import annotations

from pathlib import Path

from app.db import get_connection


def init_time_entries_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                entry_date TEXT,
                hours REAL NOT NULL,
                hourly_rate REAL NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_time_entry(
    project_id: int,
    employee_id: int,
    entry_date: str | None,
    hours: float,
    hourly_rate: float,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO time_entries (project_id, employee_id, entry_date, hours, hourly_rate)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, employee_id, entry_date, hours, hourly_rate),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_time_entries_for_project(project_id: int, db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT time_entries.*, employees.name AS employee_name
            FROM time_entries
            LEFT JOIN employees ON employees.id = time_entries.employee_id
            WHERE time_entries.project_id = ?
            ORDER BY time_entries.entry_date DESC, time_entries.id DESC
            """,
            (project_id,),
        ).fetchall()
        entries = [dict(row) for row in rows]
        for entry in entries:
            entry["cost"] = round(entry["hours"] * entry["hourly_rate"], 2)
        return entries
    finally:
        conn.close()


def get_labor_cost_total(project_id: int, db_path: Path | None = None) -> float:
    conn = get_connection(db_path)
    try:
        total = conn.execute(
            "SELECT COALESCE(SUM(hours * hourly_rate), 0) FROM time_entries WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]
        return round(total, 2)
    finally:
        conn.close()


def delete_time_entry(entry_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
