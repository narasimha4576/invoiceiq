import os
import tempfile

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from google.genai import errors
from pydantic import BaseModel

from app.extractor import MIME_TYPES, extract_with_confidence
from app.health import check_database, check_redis
from app.jobs import process_job
from app.review import check_missing_fields, review_invoice
from app.schemas import Invoice, Problem, ReviewedInvoice
from app.storage import create_job, get_job, list_invoices, list_jobs, save_invoice
from app.validators import validate_invoice

app = FastAPI(title="InvoiceIQ API")

# Uploaded invoices wait here until their job has been processed
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# "background" runs jobs inside the API; "celery" sends them to a separate worker
JOB_RUNNER = os.getenv("JOB_RUNNER", "background")


class SaveRequest(BaseModel):
    file_name: str
    original: ReviewedInvoice
    corrected: Invoice


class SaveResponse(BaseModel):
    id: int
    remaining_problems: list[Problem]


class JobCreated(BaseModel):
    job_id: str
    status: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    """Is everything this service depends on working right now?"""
    checks = {}
    failures = {}

    try:
        checks["database"] = check_database()
    except Exception as error:
        # Report only the kind of error, never its text (it could contain secrets)
        failures["database"] = type(error).__name__

    if JOB_RUNNER == "celery":
        try:
            checks["redis"] = check_redis(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        except Exception as error:
            failures["redis"] = type(error).__name__
    else:
        checks["redis"] = "not used"

    if failures:
        raise HTTPException(status_code=503, detail=failures)
    return {"status": "ok", **checks}


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


@app.post("/jobs", response_model=JobCreated, status_code=202)
def create_extraction_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a PDF, PNG or JPG file.")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    job_id = create_job(file.filename or "upload")
    path = os.path.join(UPLOAD_DIR, f"{job_id}{extension}")
    with open(path, "wb") as f:
        f.write(contents)

    if JOB_RUNNER == "celery":
        # Put a note on the Redis message board for the worker
        from app.worker import process_invoice

        process_invoice.delay(job_id, path)
    else:
        # Do the slow work after the answer has been sent
        background_tasks.add_task(process_job, job_id, path)
    return JobCreated(job_id=job_id, status="queued")


@app.get("/jobs")
def recent_jobs(status: str | None = None, limit: int = Query(20, ge=1, le=100)):
    return list_jobs(status=status, limit=limit)


@app.get("/jobs/{job_id}")
def read_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


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