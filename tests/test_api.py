import os

import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app import main, storage
from app.schemas import AIExtraction, FieldConfidence, Invoice, LineItem

calls = []  # the file paths our fake AI was asked to read


def make_extraction(**invoice_changes) -> AIExtraction:
    """Build a correct fake AI answer, then change only what a test needs."""
    invoice = dict(
        vendor_name="Test Traders",
        gstin="29ABCDE1234F1Z5",
        invoice_number="INV-001",
        invoice_date="2023-10-01",
        line_items=[
            LineItem(description="Pen", quantity=10, unit_price=5, amount=50),
            LineItem(description="Book", quantity=2, unit_price=20, amount=40),
        ],
        subtotal=90,
        tax_amount=16.2,
        total=106.2,
    )
    invoice.update(invoice_changes)
    confidence = FieldConfidence(
        vendor_name=1.0,
        gstin=1.0,
        invoice_number=1.0,
        invoice_date=1.0,
        line_items=1.0,
        subtotal=1.0,
        tax_amount=1.0,
        total=1.0,
    )
    return AIExtraction(invoice=Invoice(**invoice), confidence=confidence)


def fake_extract(path):
    calls.append(path)
    return make_extraction()


class FakeAIError(errors.APIError):
    """A stand-in for 'the AI service is busy'."""

    def __init__(self):
        Exception.__init__(self, "busy")


@pytest.fixture
def client(monkeypatch, tmp_path):
    calls.clear()
    # Use a temporary database and the fake AI for every test
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(main, "extract_with_confidence", fake_extract)
    return TestClient(main.app)


def upload(client, name="invoice.pdf", content=b"fake file bytes", kind="application/pdf"):
    return client.post("/extract", files={"file": (name, content, kind)})


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_returns_reviewed_invoice(client):
    response = upload(client)
    assert response.status_code == 200
    body = response.json()
    assert body["invoice"]["vendor_name"] == "Test Traders"
    assert body["needs_review"] is False


def test_extract_flags_a_bad_invoice(client, monkeypatch):
    monkeypatch.setattr(main, "extract_with_confidence", lambda path: make_extraction(total=110))
    body = upload(client).json()
    assert body["needs_review"] is True
    assert "total" in [p["field"] for p in body["problems"]]


def test_extract_rejects_wrong_file_type(client):
    response = upload(client, name="notes.txt", content=b"hello", kind="text/plain")
    assert response.status_code == 400
    assert "PDF, PNG or JPG" in response.json()["detail"]


def test_extract_rejects_empty_file(client):
    response = upload(client, content=b"")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_extract_returns_503_when_ai_is_unavailable(client, monkeypatch):
    def broken(path):
        raise FakeAIError()

    monkeypatch.setattr(main, "extract_with_confidence", broken)
    response = upload(client)
    assert response.status_code == 503


def test_temporary_file_is_deleted(client):
    upload(client)
    assert len(calls) == 1
    assert not os.path.exists(calls[0])


def test_list_is_empty_at_the_start(client):
    assert client.get("/invoices").json() == []


def test_save_and_list_invoices(client):
    reviewed = upload(client).json()
    save_response = client.post(
        "/invoices",
        json={"file_name": "invoice.pdf", "original": reviewed, "corrected": reviewed["invoice"]},
    )
    assert save_response.status_code == 200
    assert save_response.json()["remaining_problems"] == []

    listing = client.get("/invoices").json()
    assert len(listing) == 1
    assert listing[0]["file_name"] == "invoice.pdf"


def test_save_reports_remaining_problems(client):
    reviewed = upload(client).json()
    corrected = dict(reviewed["invoice"], total=500)
    response = client.post(
        "/invoices",
        json={"file_name": "invoice.pdf", "original": reviewed, "corrected": corrected},
    )
    assert response.status_code == 200
    fields = [p["field"] for p in response.json()["remaining_problems"]]
    assert "total" in fields