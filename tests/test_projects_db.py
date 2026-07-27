from app import company_settings, customers_db, db, documents_db, projects_db

SAMPLE_CUSTOMER = {
    "name": "Muster Immobilien GmbH",
    "street": "Musterstraße 1",
    "zip_code": "10719",
    "city": "Berlin",
}

SAMPLE_PROJECT = {
    "name": "Sanierung Musterstraße 5",
    "street": "Musterstraße 5",
    "zip_code": "10719",
    "city": "Berlin",
    "status": "aktiv",
    "start_date": "01.03.2026",
}


def _setup(tmp_path):
    db_path = tmp_path / "test.db"
    customers_db.init_customers_table(db_path)
    projects_db.init_projects_table(db_path)
    db.init_db(db_path)
    company_settings.init_company_settings_table(db_path)
    documents_db.init_documents_tables(db_path)
    return db_path


def test_create_and_get_project(tmp_path):
    db_path = _setup(tmp_path)

    project_id = projects_db.create_project(SAMPLE_PROJECT, db_path)
    stored = projects_db.get_project(project_id, db_path)

    assert stored["name"] == "Sanierung Musterstraße 5"
    assert stored["status"] == "aktiv"


def test_create_project_defaults_status_to_aktiv(tmp_path):
    db_path = _setup(tmp_path)

    project_id = projects_db.create_project({"name": "Ohne Status"}, db_path)

    assert projects_db.get_project(project_id, db_path)["status"] == "aktiv"


def test_project_with_customer_includes_customer_name(tmp_path):
    db_path = _setup(tmp_path)
    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)

    project_id = projects_db.create_project(
        {**SAMPLE_PROJECT, "customer_id": customer_id}, db_path
    )

    project = projects_db.get_project(project_id, db_path)
    assert project["customer_name"] == "Muster Immobilien GmbH"


def test_list_projects(tmp_path):
    db_path = _setup(tmp_path)
    projects_db.create_project(SAMPLE_PROJECT, db_path)
    projects_db.create_project({**SAMPLE_PROJECT, "name": "Zweites Projekt"}, db_path)

    projects = projects_db.list_projects(db_path)

    assert len(projects) == 2


def test_update_project(tmp_path):
    db_path = _setup(tmp_path)
    project_id = projects_db.create_project(SAMPLE_PROJECT, db_path)

    updated = projects_db.update_project(
        project_id, {**SAMPLE_PROJECT, "status": "abgeschlossen"}, db_path
    )

    assert updated is True
    assert projects_db.get_project(project_id, db_path)["status"] == "abgeschlossen"


def test_update_unknown_project_returns_false(tmp_path):
    db_path = _setup(tmp_path)
    assert projects_db.update_project(9999, SAMPLE_PROJECT, db_path) is False


def test_delete_project(tmp_path):
    db_path = _setup(tmp_path)
    project_id = projects_db.create_project(SAMPLE_PROJECT, db_path)

    deleted = projects_db.delete_project(project_id, db_path)

    assert deleted is True
    assert projects_db.get_project(project_id, db_path) is None


def test_delete_unknown_project_returns_false(tmp_path):
    db_path = _setup(tmp_path)
    assert projects_db.delete_project(9999, db_path) is False


def test_delete_project_unlinks_invoices_and_documents(tmp_path):
    db_path = _setup(tmp_path)
    db.init_db(db_path)
    company_settings.init_company_settings_table(db_path)
    documents_db.init_documents_tables(db_path)

    project_id = projects_db.create_project(SAMPLE_PROJECT, db_path)
    customer_id = customers_db.create_customer(SAMPLE_CUSTOMER, db_path)

    invoice_id = db.save_invoice({"supplier": "Foo GmbH", "total_amount": 100.0}, db_path)
    db.assign_invoice_project(invoice_id, project_id, db_path)

    document_id = documents_db.create_document(
        "angebot",
        customer_id,
        [{"description": "Test", "quantity": 1, "unit_price": 50.0, "tax_rate": 19.0}],
        project_id=project_id,
        db_path=db_path,
    )

    projects_db.delete_project(project_id, db_path)

    assert db.get_invoice(invoice_id, db_path)["project_id"] is None
    assert documents_db.get_document(document_id, db_path)["project_id"] is None
