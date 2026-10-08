import logging
import os

from google.genai import errors

from app.extractor import extract_with_confidence
from app.review import review_invoice
from app.storage import update_job

logger = logging.getLogger(__name__)


def process_job(job_id: str, path: str) -> None:
    """Read one uploaded invoice and store the outcome on its job."""
    update_job(job_id, "processing")
    try:
        extraction = extract_with_confidence(path)
        result = review_invoice(extraction)
        update_job(job_id, "done", result=result.model_dump())
    except errors.APIError:
        update_job(job_id, "failed", error="The AI service is busy or unavailable. Please try again.")
    except Exception:
        logger.exception("Job %s failed", job_id)
        update_job(job_id, "failed", error="Something went wrong while reading the invoice.")
    finally:
        # Do not keep uploaded invoices lying around
        if os.path.exists(path):
            os.remove(path)