import os
import time

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from app.config import MODEL_NAME
from app.schemas import AIExtraction, Invoice

load_dotenv()
_client = None


def _get_client():
    # Create the AI client only when it is first needed (not when the file is imported)
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

EXTRACTION_PROMPT = """You are reading an invoice. Extract the fields into the requested JSON format.
Rules:
- Only return a value if you can clearly SEE all of it printed in the image or document.
- If a value is cut off, partly hidden, blurry, or touching the edge of the image, return null for it.
- Never calculate or infer a value. Do not work out amounts from quantity x rate, from percentages, or from other totals.
- Amounts must be plain numbers with no currency symbols or commas.
- invoice_date: copy it exactly as written on the invoice.
- gstin: copy it exactly as written.
- tax_amount: the total of all tax lines you can see (for example CGST + SGST, or IGST, or GST). If no tax amount is visible, use null.
- Include every line item row you can see, using null for any cell that is cut off."""


def _load_part(path: str) -> types.Part:
    extension = os.path.splitext(path)[1].lower()
    mime_type = MIME_TYPES[extension]
    with open(path, "rb") as f:
        data = f.read()
    return types.Part.from_bytes(data=data, mime_type=mime_type)


def _call_model(contents, config=None, tries: int = 3):
    # If Google says "busy" (a server error), wait a few seconds and try again.
    for attempt in range(tries):
        try:
            return _get_client().models.generate_content(
                model=MODEL_NAME, contents=contents, config=config
            )
        except (errors.ServerError, httpx.TransportError):
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def read_invoice(path: str) -> str:
    part = _load_part(path)
    response = _call_model([part, "Read this invoice and write out all the text and numbers you can see."])
    return response.text


def extract_invoice(path: str) -> Invoice:
    part = _load_part(path)
    response = _call_model(
        [part, EXTRACTION_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Invoice,
            temperature=0,
        ),
    )
    return Invoice.model_validate_json(response.text)

CONFIDENCE_PROMPT = EXTRACTION_PROMPT + """

Also fill in "confidence": a number from 0 to 1 for each field, saying how sure you are that the value you returned is exactly right and complete.
- 1.0 only if the whole value is fully visible and clear.
- 0.5 or lower if any part is cut off, blurry, hard to read, or you are unsure.
- 0.0 if the value is null.
For line_items, give one overall confidence for the whole table."""


def extract_with_confidence(path: str) -> AIExtraction:
    part = _load_part(path)
    response = _call_model(
        [part, CONFIDENCE_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AIExtraction,
            temperature=0,
        ),
    )
    return AIExtraction.model_validate_json(response.text)