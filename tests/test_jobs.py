import pytest
from google.genai import errors

from app import jobs, storage, worker


class FakeBusyError(errors.ServerError):
    """A stand-in for 'the AI service is busy' (a temporary error)."""

    def __init__(self):
        Exception.__init__(self, "busy")


@pytest.fixture
def waiting_job(tmp_path, monkeypatch):
    """A job whose AI call always fails, plus its uploaded file."""
    monkeypatch.setattr(storage, "DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")

    def broken(path):
        raise FakeBusyError()

    monkeypatch.setattr(jobs, "extract_with_confidence", broken)
    invoice_file = tmp_path / "invoice.pdf"
    invoice_file.write_bytes(b"fake file bytes")
    job_id = storage.create_job("invoice.pdf")
    return job_id, invoice_file


def test_busy_ai_without_retries_fails_the_job(waiting_job):
    job_id, invoice_file = waiting_job
    jobs.process_job(job_id, str(invoice_file), can_retry=False)
    assert storage.get_job(job_id)["status"] == "failed"
    assert not invoice_file.exists()


def test_busy_ai_with_retries_keeps_the_job_and_file(waiting_job):
    job_id, invoice_file = waiting_job
    with pytest.raises(jobs.AIBusyError):
        jobs.process_job(job_id, str(invoice_file), can_retry=True)
    assert storage.get_job(job_id)["status"] == "retrying"
    assert invoice_file.exists()


def test_worker_task_asks_celery_to_retry(waiting_job):
    job_id, invoice_file = waiting_job
    with pytest.raises(jobs.AIBusyError):
        worker.process_invoice(job_id, str(invoice_file))
    assert storage.get_job(job_id)["status"] == "retrying"


def test_other_errors_fail_the_job_without_retrying(waiting_job, monkeypatch):
    job_id, invoice_file = waiting_job

    def crash(path):
        raise ValueError("something unexpected")

    monkeypatch.setattr(jobs, "extract_with_confidence", crash)
    jobs.process_job(job_id, str(invoice_file), can_retry=True)

    job = storage.get_job(job_id)
    assert job["status"] == "failed"
    assert "Something went wrong" in job["error"]
    assert not invoice_file.exists()