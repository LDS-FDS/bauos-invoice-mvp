from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from app import documents_db, projects_db, time_entries_db
from app.db import list_invoices

SKONTO_REMINDER_DAYS = 3
UPCOMING_DAYS = 7

_OPEN_REVENUE_STATUSES = {"versendet"}


def _parse_german_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def _document_amount_due(document: dict) -> float:
    amount = document.get("amount_due")
    if amount is None:
        amount = document.get("gross_total") or 0
    return amount or 0


def build_dashboard_summary(db_path: Path | None = None, today: date | None = None) -> dict:
    today = today or date.today()
    skonto_horizon = today + timedelta(days=SKONTO_REMINDER_DAYS)
    upcoming_horizon = today + timedelta(days=UPCOMING_DAYS)

    invoices = list_invoices(db_path=db_path)
    documents = documents_db.list_documents(db_path=db_path)
    projects = projects_db.list_projects(db_path=db_path)

    open_invoices = [i for i in invoices if i["status"] == "offen"]
    overdue_invoices = []
    skonto_soon_invoices = []
    for invoice in open_invoices:
        due = _parse_german_date(invoice.get("due_date"))
        if due and due < today:
            overdue_invoices.append(invoice)
        skonto_date = _parse_german_date(invoice.get("skonto_date"))
        if skonto_date and today <= skonto_date <= skonto_horizon:
            skonto_soon_invoices.append(invoice)

    invoices_open_sum = round(sum(i["total_amount"] or 0 for i in open_invoices), 2)
    invoices_overdue_sum = round(sum(i["total_amount"] or 0 for i in overdue_invoices), 2)
    invoices_skonto_soon_savings = round(
        sum(
            (i["total_amount"] or 0) - (i.get("amount_with_skonto") or i["total_amount"] or 0)
            for i in skonto_soon_invoices
        ),
        2,
    )

    open_revenue_docs = [
        d
        for d in documents
        if d["doc_type"] in ("rechnung", "abschlagsrechnung")
        and d["status"] in _OPEN_REVENUE_STATUSES
    ]
    overdue_revenue_docs = []
    for doc in open_revenue_docs:
        due = _parse_german_date(doc.get("due_date"))
        if due and due < today:
            overdue_revenue_docs.append(doc)

    draft_documents = [d for d in documents if d["status"] == "entwurf"]

    revenue_open_sum = round(sum(_document_amount_due(d) for d in open_revenue_docs), 2)
    revenue_overdue_sum = round(sum(_document_amount_due(d) for d in overdue_revenue_docs), 2)

    active_projects = [p for p in projects if p["status"] == "aktiv"]
    project_balances = []
    total_balance = 0.0
    for project in active_projects:
        project_id = project["id"]
        project_invoices = list_invoices(project_id, db_path=db_path)
        project_documents = documents_db.list_documents(project_id=project_id, db_path=db_path)
        costs = sum(i["total_amount"] or 0 for i in project_invoices)
        revenue = sum(
            d["gross_total"] or 0 for d in project_documents if d["doc_type"] == "rechnung"
        )
        labor_cost = time_entries_db.get_labor_cost_total(project_id, db_path=db_path)
        balance = round(revenue - costs - labor_cost, 2)
        total_balance += balance
        project_balances.append({"id": project_id, "name": project["name"], "balance": balance})
    project_balances.sort(key=lambda p: p["balance"])

    upcoming = []
    for invoice in open_invoices:
        due = _parse_german_date(invoice.get("due_date"))
        if due and due <= upcoming_horizon:
            upcoming.append(
                {
                    "kind": "eingang",
                    "label": invoice.get("supplier") or "Unbekannter Lieferant",
                    "reference": invoice.get("invoice_number"),
                    "due_date": invoice.get("due_date"),
                    "amount": invoice.get("total_amount"),
                    "overdue": due < today,
                }
            )
    for doc in open_revenue_docs:
        due = _parse_german_date(doc.get("due_date"))
        if due and due <= upcoming_horizon:
            upcoming.append(
                {
                    "kind": "ausgang",
                    "label": doc.get("customer_name") or "Unbekannter Kunde",
                    "reference": doc.get("doc_number"),
                    "due_date": doc.get("due_date"),
                    "amount": _document_amount_due(doc),
                    "overdue": due < today,
                }
            )
    upcoming.sort(key=lambda u: _parse_german_date(u["due_date"]) or today)

    return {
        "invoices_open_count": len(open_invoices),
        "invoices_open_sum": invoices_open_sum,
        "invoices_overdue_count": len(overdue_invoices),
        "invoices_overdue_sum": invoices_overdue_sum,
        "invoices_skonto_soon_count": len(skonto_soon_invoices),
        "invoices_skonto_soon_savings": invoices_skonto_soon_savings,
        "revenue_open_count": len(open_revenue_docs),
        "revenue_open_sum": revenue_open_sum,
        "revenue_overdue_count": len(overdue_revenue_docs),
        "revenue_overdue_sum": revenue_overdue_sum,
        "drafts_count": len(draft_documents),
        "active_projects_count": len(active_projects),
        "active_projects_balance": round(total_balance, 2),
        "project_balances": project_balances[:5],
        "upcoming": upcoming[:8],
    }
