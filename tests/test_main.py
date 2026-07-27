import pytest
from fastapi.testclient import TestClient

from app import company_settings, customers_db, db, documents_db, projects_db
from app import main as main_module
from app.ai_invoice_extractor import AIInvoiceData
from app.invoice_parser import InvoiceData
from app.main import _build_response, app

SAMPLE_INVOICE = {
    "supplier": "Foo GmbH",
    "invoice_number": "1",
    "invoice_date": "01.01.2026",
    "total_amount": 100.0,
    "currency": "EUR",
    "due_date": "01.02.2026",
    "skonto_percent": None,
    "skonto_date": None,
    "amount_with_skonto": None,
    "bank_account": None,
    "bank_name": None,
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", tmp_path / "test.db")
    db.init_db()
    customers_db.init_customers_table()
    company_settings.init_company_settings_table()
    projects_db.init_projects_table()
    documents_db.init_documents_tables()
    return TestClient(app)


def test_build_response_computes_amount_with_skonto():
    data = InvoiceData(
        supplier="Mustermann Bau GmbH",
        invoice_number="2026-045",
        invoice_date="01.07.2026",
        total_amount=4250.00,
        currency="EUR",
        due_date="31.07.2026",
        skonto_percent=2.0,
        skonto_date="10.07.2026",
        skonto_amount=None,
        bank_account="DE89370400440532013000",
        bank_name="Musterbank",
    )

    response = _build_response(data)

    assert response["amount_with_skonto"] == 4165.00
    assert response["bank_name"] == "Musterbank"


def test_build_response_prefers_stated_skonto_amount():
    data = InvoiceData(
        supplier="STARK Deutschland GmbH",
        invoice_number="1",
        invoice_date="22.07.2026",
        total_amount=3.84,
        currency="EUR",
        due_date="06.08.2026",
        skonto_percent=2.0,
        skonto_date="30.07.2026",
        skonto_amount=3.78,
        bank_account=None,
        bank_name=None,
    )

    response = _build_response(data)

    assert response["amount_with_skonto"] == 3.78


def test_build_response_without_skonto_has_no_amount_with_skonto():
    data = InvoiceData(
        supplier="Mustermann Bau GmbH",
        invoice_number=None,
        invoice_date=None,
        total_amount=1000.00,
        currency="EUR",
        due_date=None,
        skonto_percent=None,
        skonto_date=None,
        skonto_amount=None,
        bank_account=None,
        bank_name=None,
    )

    response = _build_response(data)

    assert response["amount_with_skonto"] is None


def test_list_invoices_empty(client):
    response = client.get("/invoices")
    assert response.status_code == 200
    assert response.json() == []


def test_invoice_status_lifecycle(client):
    invoice_id = db.save_invoice(SAMPLE_INVOICE)

    listed = client.get("/invoices").json()
    assert len(listed) == 1
    assert listed[0]["id"] == invoice_id
    assert listed[0]["status"] == "offen"

    patched = client.patch(f"/invoices/{invoice_id}", json={"status": "bezahlt"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "bezahlt"

    deleted = client.delete(f"/invoices/{invoice_id}")
    assert deleted.status_code == 200

    assert client.get("/invoices").json() == []


def test_export_invoices_pdf(client):
    db.save_invoice(SAMPLE_INVOICE)

    response = client.get("/invoices/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_invoices_pdf_when_empty(client):
    response = client.get("/invoices/export/pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_patch_unknown_invoice_returns_404(client):
    response = client.patch("/invoices/999999", json={"status": "bezahlt"})
    assert response.status_code == 404


def test_delete_unknown_invoice_returns_404(client):
    response = client.delete("/invoices/999999")
    assert response.status_code == 404


def test_scanned_pdf_uses_image_extraction(client, monkeypatch):
    monkeypatch.setattr(main_module, "_extract_text_from_pdf", lambda file_bytes: "")
    monkeypatch.setattr(main_module, "_render_first_page_as_png", lambda file_bytes: b"fake-png")
    monkeypatch.setattr(
        main_module,
        "extract_invoice_from_image",
        lambda image_bytes, client=None: AIInvoiceData(
            supplier="Dreiling Aufzugbau GmbH",
            invoice_number="20252313",
            invoice_date=None,
            total_amount=500.0,
            currency="EUR",
            due_date=None,
            skonto_percent=None,
            skonto_date=None,
            skonto_amount=None,
            bank_account=None,
            bank_name=None,
        ),
    )

    response = client.post(
        "/invoices/parse",
        files={"file": ("scan.pdf", b"%PDF-fake", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["supplier"] == "Dreiling Aufzugbau GmbH"
    assert data["total_amount"] == 500.0


SAMPLE_CUSTOMER = {
    "name": "Muster Immobilien GmbH",
    "street": "Musterstraße 1",
    "zip_code": "10719",
    "city": "Berlin",
    "email": "kontakt@muster-immobilien.de",
    "phone": "030 1234567",
}


def test_customer_lifecycle(client):
    created = client.post("/customers", json=SAMPLE_CUSTOMER)
    assert created.status_code == 200
    customer_id = created.json()["id"]

    listed = client.get("/customers").json()
    assert len(listed) == 1
    assert listed[0]["name"] == "Muster Immobilien GmbH"

    fetched = client.get(f"/customers/{customer_id}")
    assert fetched.status_code == 200
    assert fetched.json()["city"] == "Berlin"

    updated = client.patch(
        f"/customers/{customer_id}", json={**SAMPLE_CUSTOMER, "city": "Hamburg"}
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Hamburg"

    deleted = client.delete(f"/customers/{customer_id}")
    assert deleted.status_code == 200
    assert client.get("/customers").json() == []


def test_get_unknown_customer_returns_404(client):
    response = client.get("/customers/999999")
    assert response.status_code == 404


def test_update_unknown_customer_returns_404(client):
    response = client.patch("/customers/999999", json=SAMPLE_CUSTOMER)
    assert response.status_code == 404


def test_delete_unknown_customer_returns_404(client):
    response = client.delete("/customers/999999")
    assert response.status_code == 404


def test_company_settings_defaults_to_empty(client):
    response = client.get("/company-settings")
    assert response.status_code == 200
    assert response.json()["name"] is None


def test_company_settings_save_and_retrieve(client):
    settings = {
        "name": "CIDE Concept GmbH",
        "street": "Knesebeckstr. 62",
        "zip_code": "10719",
        "city": "Berlin",
        "email": "info@cide-concept.de",
        "phone": "030 1234567",
        "tax_id": "DE123456789",
        "bank_name": "Musterbank",
        "bank_iban": "DE89370400440532013000",
    }

    saved = client.put("/company-settings", json=settings)
    assert saved.status_code == 200
    assert saved.json()["name"] == "CIDE Concept GmbH"

    fetched = client.get("/company-settings")
    assert fetched.json()["bank_iban"] == "DE89370400440532013000"


SAMPLE_ITEMS = [
    {"description": "Trockenbauarbeiten", "quantity": 10, "unit": "Std.", "unit_price": 45.0, "tax_rate": 19.0},
]


def _create_customer(client) -> int:
    return client.post("/customers", json=SAMPLE_CUSTOMER).json()["id"]


def test_create_document_requires_existing_customer(client):
    response = client.post(
        "/documents",
        json={"doc_type": "angebot", "customer_id": 9999, "items": SAMPLE_ITEMS},
    )
    assert response.status_code == 404


def test_create_document_requires_items(client):
    customer_id = _create_customer(client)
    response = client.post(
        "/documents", json={"doc_type": "angebot", "customer_id": customer_id, "items": []}
    )
    assert response.status_code == 400


def test_document_lifecycle(client):
    customer_id = _create_customer(client)

    created = client.post(
        "/documents",
        json={"doc_type": "angebot", "customer_id": customer_id, "items": SAMPLE_ITEMS},
    )
    assert created.status_code == 200
    document = created.json()
    assert document["doc_number"].startswith("ANG-")
    assert document["status"] == "entwurf"
    assert document["gross_total"] == 535.5

    listed = client.get("/documents").json()
    assert len(listed) == 1

    fetched = client.get(f"/documents/{document['id']}")
    assert fetched.status_code == 200
    assert len(fetched.json()["items"]) == 1

    patched = client.patch(f"/documents/{document['id']}", json={"status": "angenommen"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "angenommen"

    pdf_response = client.get(f"/documents/{document['id']}/pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    deleted = client.delete(f"/documents/{document['id']}")
    assert deleted.status_code == 200
    assert client.get("/documents").json() == []


def test_get_unknown_document_returns_404(client):
    assert client.get("/documents/9999").status_code == 404


def test_update_unknown_document_returns_404(client):
    response = client.patch("/documents/9999", json={"status": "angenommen"})
    assert response.status_code == 404


def test_delete_unknown_document_returns_404(client):
    assert client.delete("/documents/9999").status_code == 404


def test_document_pdf_for_unknown_document_returns_404(client):
    assert client.get("/documents/9999/pdf").status_code == 404


def test_convert_angebot_to_invoice_endpoint(client):
    customer_id = _create_customer(client)
    angebot = client.post(
        "/documents",
        json={"doc_type": "angebot", "customer_id": customer_id, "items": SAMPLE_ITEMS},
    ).json()

    response = client.post(f"/documents/{angebot['id']}/convert-to-invoice")

    assert response.status_code == 200
    invoice = response.json()
    assert invoice["doc_type"] == "rechnung"
    assert invoice["converted_from_id"] == angebot["id"]


def test_convert_invoice_returns_400(client):
    customer_id = _create_customer(client)
    rechnung = client.post(
        "/documents",
        json={"doc_type": "rechnung", "customer_id": customer_id, "items": SAMPLE_ITEMS},
    ).json()

    response = client.post(f"/documents/{rechnung['id']}/convert-to-invoice")

    assert response.status_code == 400


SAMPLE_PROJECT = {
    "name": "Sanierung Musterstraße 5",
    "street": "Musterstraße 5",
    "zip_code": "10719",
    "city": "Berlin",
    "status": "aktiv",
}


def test_project_lifecycle(client):
    created = client.post("/projects", json=SAMPLE_PROJECT)
    assert created.status_code == 200
    project_id = created.json()["id"]
    assert created.json()["status"] == "aktiv"

    listed = client.get("/projects").json()
    assert len(listed) == 1

    fetched = client.get(f"/projects/{project_id}")
    assert fetched.status_code == 200

    updated = client.patch(
        f"/projects/{project_id}", json={**SAMPLE_PROJECT, "status": "abgeschlossen"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "abgeschlossen"

    deleted = client.delete(f"/projects/{project_id}")
    assert deleted.status_code == 200
    assert client.get("/projects").json() == []


def test_get_unknown_project_returns_404(client):
    assert client.get("/projects/9999").status_code == 404


def test_create_project_with_unknown_customer_returns_404(client):
    response = client.post("/projects", json={**SAMPLE_PROJECT, "customer_id": 9999})
    assert response.status_code == 404


def test_update_unknown_project_returns_404(client):
    response = client.patch("/projects/9999", json=SAMPLE_PROJECT)
    assert response.status_code == 404


def test_delete_unknown_project_returns_404(client):
    assert client.delete("/projects/9999").status_code == 404


def test_assign_invoice_to_project(client):
    project_id = client.post("/projects", json=SAMPLE_PROJECT).json()["id"]
    invoice_id = db.save_invoice(SAMPLE_INVOICE)

    response = client.put(f"/invoices/{invoice_id}/project", json={"project_id": project_id})
    assert response.status_code == 200
    assert response.json()["project_id"] == project_id

    filtered = client.get(f"/invoices?project_id={project_id}").json()
    assert len(filtered) == 1


def test_assign_invoice_to_unknown_project_returns_404(client):
    invoice_id = db.save_invoice(SAMPLE_INVOICE)
    response = client.put(f"/invoices/{invoice_id}/project", json={"project_id": 9999})
    assert response.status_code == 404


def test_assign_project_to_unknown_invoice_returns_404(client):
    project_id = client.post("/projects", json=SAMPLE_PROJECT).json()["id"]
    response = client.put("/invoices/9999/project", json={"project_id": project_id})
    assert response.status_code == 404


def test_create_document_with_unknown_project_returns_404(client):
    customer_id = _create_customer(client)
    response = client.post(
        "/documents",
        json={
            "doc_type": "angebot",
            "customer_id": customer_id,
            "items": SAMPLE_ITEMS,
            "project_id": 9999,
        },
    )
    assert response.status_code == 404


def test_assign_document_to_project(client):
    customer_id = _create_customer(client)
    project_id = client.post("/projects", json=SAMPLE_PROJECT).json()["id"]
    document = client.post(
        "/documents",
        json={"doc_type": "angebot", "customer_id": customer_id, "items": SAMPLE_ITEMS},
    ).json()

    response = client.put(f"/documents/{document['id']}/project", json={"project_id": project_id})
    assert response.status_code == 200
    assert response.json()["project_id"] == project_id

    filtered = client.get(f"/documents?project_id={project_id}").json()
    assert len(filtered) == 1


def test_project_summary(client):
    customer_id = _create_customer(client)
    project_id = client.post("/projects", json=SAMPLE_PROJECT).json()["id"]

    invoice_id = db.save_invoice({**SAMPLE_INVOICE, "total_amount": 100.0})
    client.put(f"/invoices/{invoice_id}/project", json={"project_id": project_id})

    document = client.post(
        "/documents",
        json={
            "doc_type": "rechnung",
            "customer_id": customer_id,
            "items": SAMPLE_ITEMS,
            "project_id": project_id,
        },
    ).json()

    summary = client.get(f"/projects/{project_id}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["costs"] == 100.0
    assert data["revenue"] == document["gross_total"]
    assert len(data["invoices"]) == 1
    assert len(data["documents"]) == 1


def test_project_summary_unknown_project_returns_404(client):
    assert client.get("/projects/9999/summary").status_code == 404
