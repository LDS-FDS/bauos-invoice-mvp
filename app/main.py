import io

import pdfplumber
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.ai_invoice_extractor import extract_invoice_with_ai
from app.invoice_parser import parse_invoice_text

app = FastAPI(title="BauOS Invoice MVP")


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _build_response(data) -> dict:
    amount_with_skonto = None
    if data.total_amount is not None and data.skonto_percent is not None:
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
    }


@app.post("/invoices/parse")
async def parse_invoice(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    text = _extract_text_from_pdf(file_bytes)

    result = parse_invoice_text(text)
    if result.total_amount is None:
        result = extract_invoice_with_ai(text)
    return _build_response(result)
