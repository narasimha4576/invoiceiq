from datetime import datetime, timezone

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

# This table lives in the same database as the rest of the data
from app.storage import Base, _engine


class UsageRecord(Base):
    __tablename__ = "daily_usage"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # for example 2026-10-12
    ai_calls: Mapped[int] = mapped_column(Integer, default=0)


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def allow_ai_call(limit: int) -> bool:
    """Count one AI call for today. Returns False when today's limit is already used up."""
    if limit <= 0:
        return True  # no limit configured

    with Session(_engine()) as session:
        record = session.get(UsageRecord, today())
        if record is None:
            record = UsageRecord(day=today(), ai_calls=0)
            session.add(record)
        if record.ai_calls >= limit:
            return False
        record.ai_calls += 1
        session.commit()
        return True