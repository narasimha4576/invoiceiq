import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from google.genai import errors
from pydantic import BaseModel

from app.extractor import MIME_TYPES, extract_with_confidence
from app.review import check_missing_fields, review_invoice
from app.schemas import Invoice, Problem, ReviewedInvoice
from app.storage import list_invoices, save_invoice
from app.validators import validate_invoice

app = FastAPI(title="InvoiceIQ API")


class SaveRequest(BaseModel):
    file_name: str
    original: ReviewedInvoice
    corrected: Invoice


class SaveResponse(BaseModel):
    id: int
    remaining_problems: list[Problem]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract", response_model=ReviewedInvoice)
def extract(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a PDF, PNG or JPG file.")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # Save the upload to a temporary file so our extractor can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(contents)
        temp_path = tmp.name

    try:
        extraction = extract_with_confidence(temp_path)
        return review_invoice(extraction)
    except errors.APIError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy or unavailable. Please try again.",
        )
    finally:
        os.remove(temp_path)


@app.post("/invoices", response_model=SaveResponse)
def save(request: SaveRequest):
    # Re-check the human-corrected invoice with the same validators
    remaining = validate_invoice(request.corrected) + check_missing_fields(request.corrected)
    invoice_id = save_invoice(
        file_name=request.file_name,
        original=request.original.model_dump(),
        corrected=request.corrected.model_dump(),
        needs_review=request.original.needs_review,
    )
    return SaveResponse(id=invoice_id, remaining_problems=remaining)


@app.get("/invoices")
def invoices():
    return list_invoices()