import redis
from sqlalchemy import create_engine, text

from app import storage


def check_database() -> str:
    """Raises an error if the database cannot be reached."""
    engine = create_engine(storage.DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return "ok"


def check_redis(redis_url: str) -> str:
    """Raises an error if Redis cannot be reached."""
    client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
    client.ping()
    return "ok"