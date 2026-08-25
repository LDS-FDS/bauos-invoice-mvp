from app import db, projects_db

SAMPLE_DATA = {
    "supplier": "Mustermann Bau GmbH",
    "invoice_number": "2026-045",
    "invoice_date": "01.07.2026",
    "total_amount": 4250.00,
    "currency": "EUR",
    "due_date": "31.07.2026",
    "skonto_percent": 2.0,
    "skonto_date": "10.07.2026",
    "amount_with_skonto": 4165.00,
    "bank_account": "DE89370400440532013000",
}


def test_save_and_get_invoice(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)

    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)
    stored = db.get_invoice(invoice_id, db_path)

    assert stored["supplier"] == "Mustermann Bau GmbH"
    assert stored["status"] == "offen"


def test_list_invoices_orders_newest_first(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    projects_db.init_projects_table(db_path)

    first_id = db.save_invoice(SAMPLE_DATA, db_path)
    second_id = db.save_invoice({**SAMPLE_DATA, "invoice_number": "2026-046"}, db_path)

    invoices = db.list_invoices(db_path=db_path)

    assert [inv["id"] for inv in invoices] == [second_id, first_id]


def test_update_status(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)

    updated = db.update_status(invoice_id, "bezahlt", db_path=db_path)

    assert updated is True
    assert db.get_invoice(invoice_id, db_path)["status"] == "bezahlt"


def test_update_status_unknown_id_returns_false(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)

    assert db.update_status(9999, "bezahlt", db_path=db_path) is False


def test_update_status_to_bezahlt_sets_paid_date_and_skonto_flag(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)

    db.update_status(invoice_id, "bezahlt", paid_with_skonto=True, db_path=db_path)

    stored = db.get_invoice(invoice_id, db_path)
    assert stored["paid_with_skonto"] == 1
    assert stored["paid_date"] is not None


def test_update_status_does_not_overwrite_existing_paid_date(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)

    db.update_status(invoice_id, "bezahlt", paid_with_skonto=True, db_path=db_path)
    first_paid_date = db.get_invoice(invoice_id, db_path)["paid_date"]

    db.update_status(invoice_id, "bezahlt", paid_with_skonto=False, db_path=db_path)
    stored = db.get_invoice(invoice_id, db_path)

    assert stored["paid_date"] == first_paid_date
    assert stored["paid_with_skonto"] == 0


def test_delete_invoice(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)

    deleted = db.delete_invoice(invoice_id, db_path)

    assert deleted is True
    assert db.get_invoice(invoice_id, db_path) is None


def test_assign_invoice_project_and_filter(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    projects_db.init_projects_table(db_path)
    project_id = projects_db.create_project({"name": "Testprojekt"}, db_path)

    matched_id = db.save_invoice(SAMPLE_DATA, db_path)
    other_id = db.save_invoice({**SAMPLE_DATA, "invoice_number": "2026-046"}, db_path)
    db.assign_invoice_project(matched_id, project_id, db_path)

    filtered = db.list_invoices(project_id, db_path)

    assert [inv["id"] for inv in filtered] == [matched_id]
    assert filtered[0]["project_name"] == "Testprojekt"
    assert db.get_invoice(other_id, db_path)["project_id"] is None


def test_assign_invoice_project_unknown_id_returns_false(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    assert db.assign_invoice_project(9999, None, db_path) is False


def test_update_invoice_fields(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    invoice_id = db.save_invoice(SAMPLE_DATA, db_path)

    updated = db.update_invoice_fields(
        invoice_id,
        {
            "invoice_number": SAMPLE_DATA["invoice_number"],
            "invoice_date": SAMPLE_DATA["invoice_date"],
            "total_amount": 173.73,
            "due_date": SAMPLE_DATA["due_date"],
            "skonto_percent": 6.6,
            "skonto_date": SAMPLE_DATA["skonto_date"],
            "amount_with_skonto": 162.27,
        },
        db_path,
    )

    stored = db.get_invoice(invoice_id, db_path)
    assert updated is True
    assert stored["total_amount"] == 173.73
    assert stored["amount_with_skonto"] == 162.27
    assert stored["skonto_percent"] == 6.6


def test_update_invoice_fields_unknown_id_returns_false(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    assert db.update_invoice_fields(9999, {"total_amount": 100.0}, db_path) is False
