import io
from typing import Literal

import pdfplumber
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app import company_settings, customers_db, db, documents_db, projects_db
from app.ai_invoice_extractor import extract_invoice_from_image, extract_invoice_with_ai
from app.document_pdf import build_document_pdf
from app.invoice_parser import parse_invoice_text
from app.pdf_export import build_invoice_list_pdf

app = FastAPI(title="BauOS Invoice MVP")
db.init_db()
customers_db.init_customers_table()
company_settings.init_company_settings_table()
projects_db.init_projects_table()
documents_db.init_documents_tables()


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
def get_invoices(project_id: int | None = None) -> list[dict]:
    return db.list_invoices(project_id)


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


class ProjectAssignment(BaseModel):
    project_id: int | None = None


@app.put("/invoices/{invoice_id}/project")
def assign_invoice_project(invoice_id: int, body: ProjectAssignment) -> dict:
    if body.project_id is not None and projects_db.get_project(body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not db.assign_invoice_project(invoice_id, body.project_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db.get_invoice(invoice_id)


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
    default_payment_term_days: int | None = None


@app.get("/company-settings")
def get_company_settings() -> dict:
    return company_settings.get_company_settings()


@app.put("/company-settings")
def save_company_settings(settings: CompanySettingsIn) -> dict:
    return company_settings.save_company_settings(settings.model_dump())


class DocumentItemIn(BaseModel):
    description: str
    quantity: float
    unit: str | None = None
    unit_price: float
    tax_rate: float = 19.0


class DocumentCreate(BaseModel):
    doc_type: Literal["angebot", "rechnung"]
    customer_id: int
    issue_date: str | None = None
    valid_until: str | None = None
    due_date: str | None = None
    notes: str | None = None
    project_id: int | None = None
    items: list[DocumentItemIn]


class DocumentStatusUpdate(BaseModel):
    status: Literal["entwurf", "versendet", "angenommen", "abgelehnt", "bezahlt"]


@app.post("/documents")
def create_document(payload: DocumentCreate) -> dict:
    if customers_db.get_customer(payload.customer_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")
    if payload.project_id is not None and projects_db.get_project(payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    document_id = documents_db.create_document(
        doc_type=payload.doc_type,
        customer_id=payload.customer_id,
        items=[item.model_dump() for item in payload.items],
        issue_date=payload.issue_date,
        valid_until=payload.valid_until,
        due_date=payload.due_date,
        notes=payload.notes,
        project_id=payload.project_id,
    )
    return documents_db.get_document(document_id)


@app.get("/documents")
def list_documents(
    doc_type: Literal["angebot", "rechnung"] | None = None,
    project_id: int | None = None,
) -> list[dict]:
    return documents_db.list_documents(doc_type, project_id)


@app.get("/documents/{document_id}")
def get_document(document_id: int) -> dict:
    document = documents_db.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.patch("/documents/{document_id}")
def update_document_status(document_id: int, body: DocumentStatusUpdate) -> dict:
    if not documents_db.update_document_status(document_id, body.status):
        raise HTTPException(status_code=404, detail="Document not found")
    return documents_db.get_document(document_id)


@app.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict:
    if not documents_db.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": document_id}


@app.get("/documents/{document_id}/pdf")
def document_pdf(document_id: int) -> Response:
    document = documents_db.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_bytes = build_document_pdf(document, company_settings.get_company_settings())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={document['doc_number']}.pdf"
        },
    )


@app.post("/documents/{document_id}/convert-to-invoice")
def convert_document_to_invoice(document_id: int) -> dict:
    new_id = documents_db.convert_to_invoice(document_id)
    if new_id is None:
        raise HTTPException(
            status_code=400, detail="Document not found or is not an Angebot"
        )
    return documents_db.get_document(new_id)


@app.put("/documents/{document_id}/project")
def assign_document_project(document_id: int, body: ProjectAssignment) -> dict:
    if body.project_id is not None and projects_db.get_project(body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not documents_db.assign_document_project(document_id, body.project_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return documents_db.get_document(document_id)


class ProjectIn(BaseModel):
    name: str
    customer_id: int | None = None
    street: str | None = None
    zip_code: str | None = None
    city: str | None = None
    status: Literal["aktiv", "abgeschlossen", "pausiert"] = "aktiv"
    start_date: str | None = None
    end_date: str | None = None
    notes: str | None = None


@app.post("/projects")
def create_project(project: ProjectIn) -> dict:
    if project.customer_id is not None and customers_db.get_customer(project.customer_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    project_id = projects_db.create_project(project.model_dump())
    return projects_db.get_project(project_id)


@app.get("/projects")
def list_projects() -> list[dict]:
    return projects_db.list_projects()


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    project = projects_db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/projects/{project_id}/summary")
def get_project_summary(project_id: int) -> dict:
    project = projects_db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    invoices = db.list_invoices(project_id)
    documents = documents_db.list_documents(project_id=project_id)

    costs = sum(inv["total_amount"] or 0 for inv in invoices)
    revenue = sum(
        doc["gross_total"] or 0 for doc in documents if doc["doc_type"] == "rechnung"
    )

    return {
        "project": project,
        "invoices": invoices,
        "documents": documents,
        "costs": round(costs, 2),
        "revenue": round(revenue, 2),
        "balance": round(revenue - costs, 2),
    }


@app.patch("/projects/{project_id}")
def update_project(project_id: int, project: ProjectIn) -> dict:
    if project.customer_id is not None and customers_db.get_customer(project.customer_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not projects_db.update_project(project_id, project.model_dump()):
        raise HTTPException(status_code=404, detail="Project not found")
    return projects_db.get_project(project_id)


class ProjectStatusUpdate(BaseModel):
    status: Literal["aktiv", "abgeschlossen", "pausiert"]


@app.patch("/projects/{project_id}/status")
def update_project_status(project_id: int, body: ProjectStatusUpdate) -> dict:
    project = projects_db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project["status"] = body.status
    projects_db.update_project(project_id, project)
    return projects_db.get_project(project_id)


@app.delete("/projects/{project_id}")
def delete_project(project_id: int) -> dict:
    if not projects_db.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": project_id}
