import os

from celery import Celery

from app.jobs import AIBusyError, process_job

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("invoiceiq", broker=REDIS_URL)
celery_app.conf.broker_connection_retry_on_startup = True
# Take one job at a time, and only confirm it after it is finished,
# so a job is not lost if the worker stops halfway
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True


@celery_app.task(name="process_invoice", bind=True, max_retries=3)
def process_invoice(self, job_id: str, path: str) -> None:
    # If the AI is busy, try again a few times, waiting longer each time
    is_last_attempt = self.request.retries >= self.max_retries
    try:
        process_job(job_id, path, can_retry=not is_last_attempt)
    except AIBusyError as error:
        wait_seconds = 30 * (self.request.retries + 1)
        raise self.retry(exc=error, countdown=wait_seconds)