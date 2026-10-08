import os

from celery import Celery

from app.jobs import process_job

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("invoiceiq", broker=REDIS_URL)
celery_app.conf.broker_connection_retry_on_startup = True
# Take one job at a time, and only confirm it after it is finished,
# so a job is not lost if the worker stops halfway
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True


@celery_app.task(name="process_invoice")
def process_invoice(job_id: str, path: str) -> None:
    process_job(job_id, path)