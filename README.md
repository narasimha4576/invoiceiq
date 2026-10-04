# InvoiceIQ

AI-powered invoice extraction. Upload an invoice (PDF, PNG or JPG) and get structured JSON back. Fields that are missing or unreadable are returned as `null` instead of being guessed.

## Features
- Reads invoices with a vision-capable AI model (Google Gemini)
- Structured output validated with Pydantic
- FastAPI backend with `/health` and `/extract` endpoints
- Runs in Docker

## Tech stack
Python, FastAPI, Pydantic, Google Gemini API, Docker

## Run locally
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Create a `.env` file containing `GEMINI_API_KEY=your_key_here`, then open http://127.0.0.1:8000/docs

## Run with Docker
```bash
docker build -t invoiceiq-api .
docker run --rm -p 8000:8000 --env-file .env invoiceiq-api
```
Then open http://localhost:8000/docs

## Samples
The `samples` folder contains fake invoices for testing.

## Status
Work in progress.