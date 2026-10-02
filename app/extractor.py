import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.config import MODEL_NAME

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def read_invoice(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    mime_type = MIME_TYPES[extension]

    with open(path, "rb") as f:
        data = f.read()

    part = types.Part.from_bytes(data=data, mime_type=mime_type)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[part, "Read this invoice and write out all the text and numbers you can see."],
    )
    return response.text