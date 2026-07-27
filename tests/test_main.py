import pytest
from fastapi.testclient import TestClient

from app import db
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
