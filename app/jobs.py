import logging
import os

from google.genai import errors

from app.extractor import extract_with_confidence
from app.review import review_invoice
from app.storage import update_job

logger = logging.getLogger(__name__)


class AIBusyError(Exception):
    """The AI service was busy. The job can be tried again later."""


def _is_temporary(error: errors.APIError) -> bool:
    # A busy or rate-limited service is worth retrying. A wrong API key is not.
    return isinstance(error, errors.ServerError) or getattr(error, "code", None) == 429


def process_job(job_id: str, path: str, can_retry: bool = False) -> None:
    """Read one uploaded invoice and store the outcome on its job."""
    update_job(job_id, "processing")
    keep_file = False
    try:
        extraction = extract_with_confidence(path)
        result = review_invoice(extraction)
        update_job(job_id, "done", result=result.model_dump())
    except errors.APIError as error:
        if can_retry and _is_temporary(error):
            # Keep the file: the job will be tried again in a moment
            keep_file = True
            update_job(job_id, "retrying")
            raise AIBusyError("The AI service is busy") from error
        update_job(job_id, "failed", error="The AI service is busy or unavailable. Please try again.")
    except Exception:
        logger.exception("Job %s failed", job_id)
        update_job(job_id, "failed", error="Something went wrong while reading the invoice.")
    finally:
        # Do not keep uploaded invoices lying around (unless we will retry)
        if not keep_file and os.path.exists(path):
            os.remove(path)