import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from google.genai import errors

from app.extractor import MIME_TYPES, extract_invoice
from app.schemas import Invoice

app = FastAPI(title="InvoiceIQ API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract", response_model=Invoice)
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
        return extract_invoice(temp_path)
    except errors.APIError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy or unavailable. Please try again.",
        )
    finally:
        os.remove(temp_path)