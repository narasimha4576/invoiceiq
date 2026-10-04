import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from google.genai import errors

from app.extractor import MIME_TYPES, extract_with_confidence
from app.review import review_invoice
from app.schemas import ReviewedInvoice

app = FastAPI(title="InvoiceIQ API")


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