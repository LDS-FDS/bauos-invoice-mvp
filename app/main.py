import io
from typing import Literal

import pdfplumber
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app import company_settings, customers_db, db
from app.ai_invoice_extractor import extract_invoice_from_image, extract_invoice_with_ai
from app.invoice_parser import parse_invoice_text
from app.pdf_export import build_invoice_list_pdf

app = FastAPI(title="BauOS Invoice MVP")
db.init_db()
customers_db.init_customers_table()
company_settings.init_company_settings_table()


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse("app/static/index.html")


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _render_first_page_as_png(file_bytes: bytes) -> bytes:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_image = pdf.pages[0].to_image(resolution=200)
        buffer = io.BytesIO()
        page_image.original.save(buffer, format="PNG")
        return buffer.getvalue()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _build_response(data) -> dict:
    amount_with_skonto = data.skonto_amount
    if amount_with_skonto is None and data.total_amount is not None and data.skonto_percent is not None:
        amount_with_skonto = round(data.total_amount * (1 - data.skonto_percent / 100), 2)

    return {
        "supplier": data.supplier,
        "invoice_number": data.invoice_number,
        "invoice_date": data.invoice_date,
        "total_amount": data.total_amount,
        "currency": data.currency,
        "due_date": data.due_date,
        "skonto_percent": data.skonto_percent,
        "amount_with_skonto": amount_with_skonto,
        "skonto_date": data.skonto_date,
        "bank_account": data.bank_account,
        "bank_name": data.bank_name,
    }


@app.post("/invoices/parse")
async def parse_invoice(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    text = _extract_text_from_pdf(file_bytes)

    if not text.strip():
        image_bytes = _render_first_page_as_png(file_bytes)
        result = extract_invoice_from_image(image_bytes)
    else:
        result = parse_invoice_text(text)
        if result.total_amount is None:
            result = extract_invoice_with_ai(text)

    response = _build_response(result)
    invoice_id = db.save_invoice(response)
    return {**response, "id": invoice_id, "status": "offen"}


@app.get("/invoices")
def get_invoices() -> list[dict]:
    return db.list_invoices()


@app.get("/invoices/export/pdf")
def export_invoices_pdf() -> Response:
    pdf_bytes = build_invoice_list_pdf(db.list_invoices())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=rechnungsuebersicht.pdf"},
    )


class StatusUpdate(BaseModel):
    status: Literal["offen", "bezahlt"]


@app.patch("/invoices/{invoice_id}")
def update_invoice_status(invoice_id: int, body: StatusUpdate) -> dict:
    if not db.update_status(invoice_id, body.status):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db.get_invoice(invoice_id)


@app.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int) -> dict:
    if not db.delete_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"deleted": invoice_id}


class CustomerIn(BaseModel):
    name: str
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None


@app.post("/customers")
def create_customer(customer: CustomerIn) -> dict:
    customer_id = customers_db.create_customer(customer.model_dump())
    return customers_db.get_customer(customer_id)


@app.get("/customers")
def list_customers() -> list[dict]:
    return customers_db.list_customers()


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int) -> dict:
    customer = customers_db.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.patch("/customers/{customer_id}")
def update_customer(customer_id: int, customer: CustomerIn) -> dict:
    if not customers_db.update_customer(customer_id, customer.model_dump()):
        raise HTTPException(status_code=404, detail="Customer not found")
    return customers_db.get_customer(customer_id)


@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int) -> dict:
    if not customers_db.delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"deleted": customer_id}


class CompanySettingsIn(BaseModel):
    name: str | None = None
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    bank_name: str | None = None
    bank_iban: str | None = None


@app.get("/company-settings")
def get_company_settings() -> dict:
    return company_settings.get_company_settings()


@app.put("/company-settings")
def save_company_settings(settings: CompanySettingsIn) -> dict:
    return company_settings.save_company_settings(settings.model_dump())
