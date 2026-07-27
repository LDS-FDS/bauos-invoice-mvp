from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from app import company_settings
from app.db import get_connection

_ITEM_COLUMNS = ["description", "quantity", "unit", "unit_price", "tax_rate"]


def _compute_default_due_date(issue_date: str, db_path: Path | None) -> str | None:
    term_days = company_settings.get_company_settings(db_path).get(
        "default_payment_term_days"
    )
    if not term_days:
        return None
    try:
        parsed = datetime.strptime(issue_date, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None
    return (parsed + timedelta(days=int(term_days))).strftime("%d.%m.%Y")


def init_documents_tables(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                doc_type TEXT NOT NULL CHECK (doc_type IN ('angebot', 'rechnung')),
                doc_number TEXT NOT NULL,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                issue_date TEXT,
                valid_until TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'entwurf',
                notes TEXT,
                converted_from_id INTEGER REFERENCES documents(id),
                net_total REAL,
                tax_total REAL,
                gross_total REAL
            )
            """
        )
        existing_columns = [
            row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        ]
        if "project_id" not in existing_columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN project_id INTEGER REFERENCES projects(id)"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT,
                unit_price REAL NOT NULL,
                tax_rate REAL NOT NULL DEFAULT 19.0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _generate_doc_number(doc_type: str, conn) -> str:
    prefix = "ANG" if doc_type == "angebot" else "RE"
    year = date.today().year
    pattern = f"{prefix}-{year}-%"
    count = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE doc_type = ? AND doc_number LIKE ?",
        (doc_type, pattern),
    ).fetchone()[0]
    return f"{prefix}-{year}-{count + 1:03d}"


def _compute_totals(items: list[dict]) -> tuple[float, float, float]:
    net_total = sum(item["quantity"] * item["unit_price"] for item in items)
    tax_total = sum(
        item["quantity"] * item["unit_price"] * item.get("tax_rate", 19.0) / 100
        for item in items
    )
    gross_total = net_total + tax_total
    return round(net_total, 2), round(tax_total, 2), round(gross_total, 2)


def create_document(
    doc_type: str,
    customer_id: int,
    items: list[dict],
    issue_date: str | None = None,
    valid_until: str | None = None,
    due_date: str | None = None,
    notes: str | None = None,
    converted_from_id: int | None = None,
    project_id: int | None = None,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        doc_number = _generate_doc_number(doc_type, conn)
        net_total, tax_total, gross_total = _compute_totals(items)
        issue_date = issue_date or date.today().strftime("%d.%m.%Y")
        if doc_type == "rechnung" and due_date is None:
            due_date = _compute_default_due_date(issue_date, db_path)

        cursor = conn.execute(
            """
            INSERT INTO documents (
                doc_type, doc_number, customer_id, issue_date, valid_until,
                due_date, status, notes, converted_from_id, project_id,
                net_total, tax_total, gross_total
            ) VALUES (?, ?, ?, ?, ?, ?, 'entwurf', ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_type, doc_number, customer_id, issue_date, valid_until,
                due_date, notes, converted_from_id, project_id,
                net_total, tax_total, gross_total,
            ),
        )
        document_id = cursor.lastrowid

        for position, item in enumerate(items):
            conn.execute(
                """
                INSERT INTO document_items (
                    document_id, position, description, quantity, unit, unit_price, tax_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    position,
                    item["description"],
                    item["quantity"],
                    item.get("unit"),
                    item["unit_price"],
                    item.get("tax_rate", 19.0),
                ),
            )
        conn.commit()
        return document_id
    finally:
        conn.close()


def list_documents(
    doc_type: str | None = None,
    project_id: int | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    conn = get_connection(db_path)
    try:
        query = """
            SELECT documents.*, customers.name AS customer_name, projects.name AS project_name
            FROM documents
            LEFT JOIN customers ON customers.id = documents.customer_id
            LEFT JOIN projects ON projects.id = documents.project_id
        """
        conditions = []
        params: list = []
        if doc_type:
            conditions.append("documents.doc_type = ?")
            params.append(doc_type)
        if project_id is not None:
            conditions.append("documents.project_id = ?")
            params.append(project_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY documents.id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def assign_document_project(
    document_id: int, project_id: int | None, db_path: Path | None = None
) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE documents SET project_id = ? WHERE id = ?", (project_id, document_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_document(document_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        doc_row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if doc_row is None:
            return None
        document = dict(doc_row)

        item_rows = conn.execute(
            "SELECT * FROM document_items WHERE document_id = ? ORDER BY position",
            (document_id,),
        ).fetchall()
        document["items"] = [dict(row) for row in item_rows]

        customer_row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (document["customer_id"],)
        ).fetchone()
        document["customer"] = dict(customer_row) if customer_row else None

        return document
    finally:
        conn.close()


def update_document_status(
    document_id: int, status: str, db_path: Path | None = None
) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE documents SET status = ? WHERE id = ?", (status, document_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_document(document_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM document_items WHERE document_id = ?", (document_id,))
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def convert_to_invoice(angebot_id: int, db_path: Path | None = None) -> int | None:
    angebot = get_document(angebot_id, db_path)
    if angebot is None or angebot["doc_type"] != "angebot":
        return None

    items = [
        {col: item[col] for col in _ITEM_COLUMNS}
        for item in angebot["items"]
    ]

    return create_document(
        doc_type="rechnung",
        customer_id=angebot["customer_id"],
        items=items,
        notes=angebot["notes"],
        converted_from_id=angebot_id,
        project_id=angebot.get("project_id"),
        db_path=db_path,
    )
