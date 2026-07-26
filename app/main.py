import io

import pdfplumber
from fastapi import FastAPI, HTTPException, UploadFile

from app.ai_invoice_extractor import extract_invoice_with_ai
from app.invoice_parser import parse_invoice_text

app = FastAPI(title="BauOS Invoice MVP")


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


@app.post("/invoices/parse")
async def parse_invoice(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    text = _extract_text_from_pdf(file_bytes)

    result = parse_invoice_text(text)
    if result.total_amount is None:
        return extract_invoice_with_ai(text)
    return result
