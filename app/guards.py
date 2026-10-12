import hmac
import os

from dotenv import load_dotenv
from fastapi import Header, HTTPException, UploadFile

from app import usage

load_dotenv()

# Protection for a public demo. Set these as environment variables on the server.
# An empty or zero value switches that protection off, so local development stays easy.
ACCESS_CODE = os.getenv("DEMO_ACCESS_CODE", "")
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "5"))
DAILY_AI_LIMIT = int(os.getenv("DAILY_AI_LIMIT", "0"))


def require_access(x_access_code: str | None = Header(default=None)) -> None:
    """If an access code is set, every request must send it in the X-Access-Code header."""
    if ACCESS_CODE and not hmac.compare_digest(
        (x_access_code or "").encode(), ACCESS_CODE.encode()
    ):
        raise HTTPException(status_code=401, detail="A valid access code is required.")


def read_upload(file: UploadFile) -> bytes:
    """Read an uploaded file, refusing anything bigger than the limit."""
    limit = int(MAX_UPLOAD_MB * 1024 * 1024)
    contents = file.file.read(limit + 1)
    if len(contents) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"The file is too large (the limit is {MAX_UPLOAD_MB:g} MB).",
        )
    return contents


def check_daily_limit() -> None:
    """Refuse the request when today's AI limit has been used up."""
    if not usage.allow_ai_call(DAILY_AI_LIMIT):
        raise HTTPException(
            status_code=429,
            detail="The daily demo limit has been reached. Please try again tomorrow.",
        )