from __future__ import annotations

from pathlib import Path

from app.db import get_connection

_COLUMNS = ["description", "unit", "unit_price", "tax_rate"]


def init_articles_table(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                description TEXT NOT NULL,
                unit TEXT,
                unit_price REAL NOT NULL DEFAULT 0,
                tax_rate REAL NOT NULL DEFAULT 19.0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_article(data: dict, db_path: Path | None = None) -> int:
    conn = get_connection(db_path)
    try:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{col}" for col in _COLUMNS)
        cursor = conn.execute(
            f"INSERT INTO articles ({columns}) VALUES ({placeholders})",
            {col: data.get(col) for col in _COLUMNS},
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_articles(db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY description COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_article(article_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_article(article_id: int, data: dict, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        assignments = ", ".join(f"{col} = :{col}" for col in _COLUMNS)
        params = {col: data.get(col) for col in _COLUMNS}
        params["id"] = article_id
        cursor = conn.execute(
            f"UPDATE articles SET {assignments} WHERE id = :id", params
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_article(article_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
