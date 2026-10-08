import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Postgres in Docker, a local SQLite file when nothing else is configured
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///invoiceiq.db")


class Base(DeclarativeBase):
    pass


class InvoiceRecord(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    original: Mapped[dict] = mapped_column(JSON)
    corrected: Mapped[dict] = mapped_column(JSON)
    needs_review: Mapped[bool] = mapped_column(Boolean)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))  # queued, processing, retrying, done, failed
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_engines = {}


def _engine():
    # Create the connection (and the tables) the first time it is needed
    url = DATABASE_URL
    if url not in _engines:
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        _engines[url] = engine
    return _engines[url]


def save_invoice(file_name: str, original: dict, corrected: dict, needs_review: bool) -> int:
    with Session(_engine()) as session:
        record = InvoiceRecord(
            file_name=file_name,
            original=original,
            corrected=corrected,
            needs_review=needs_review,
            saved_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.commit()
        return record.id


def list_invoices() -> list[dict]:
    with Session(_engine()) as session:
        records = session.scalars(select(InvoiceRecord).order_by(InvoiceRecord.id.desc())).all()
        return [
            {
                "id": r.id,
                "file_name": r.file_name,
                "original": r.original,
                "corrected": r.corrected,
                "needs_review": r.needs_review,
                "saved_at": r.saved_at.isoformat(),
            }
            for r in records
        ]


def create_job(file_name: str) -> str:
    job_id = str(uuid.uuid4())
    with Session(_engine()) as session:
        session.add(
            JobRecord(
                id=job_id,
                file_name=file_name,
                status="queued",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    return job_id


def update_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    with Session(_engine()) as session:
        job = session.get(JobRecord, job_id)
        if job is None:
            return
        job.status = status
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if status in ("done", "failed"):
            job.finished_at = datetime.now(timezone.utc)
        session.commit()


def get_job(job_id: str) -> dict | None:
    with Session(_engine()) as session:
        job = session.get(JobRecord, job_id)
        if job is None:
            return None
        return {
            "job_id": job.id,
            "file_name": job.file_name,
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }


def list_jobs(status: str | None = None, limit: int = 20) -> list[dict]:
    """The most recent jobs, newest first, optionally only those with one status."""
    with Session(_engine()) as session:
        query = select(JobRecord)
        if status is not None:
            query = query.where(JobRecord.status == status)
        query = query.order_by(JobRecord.created_at.desc()).limit(limit)
        return [
            {
                "job_id": j.id,
                "file_name": j.file_name,
                "status": j.status,
                "needs_review": j.result["needs_review"] if j.result else None,
                "error": j.error,
                "created_at": j.created_at.isoformat(),
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            }
            for j in session.scalars(query).all()
        ]