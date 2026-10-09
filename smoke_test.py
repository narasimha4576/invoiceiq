"""Check that a running InvoiceIQ system works from end to end.

Usage:
    python smoke_test.py                      (tests http://127.0.0.1:8000)
    python smoke_test.py https://your-url     (tests another address)

Run it from the project folder. It uses the sample invoices and the real AI,
so it takes about a minute.
"""
import os
import sys
import time

import requests

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def step(message):
    print(f"- {message}")


def fail(message):
    print(f"FAILED: {message}")
    sys.exit(1)


def run_job(path, content_type):
    """Upload an invoice, wait for its job to finish, return the result."""
    with open(path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/jobs",
            files={"file": (os.path.basename(path), f, content_type)},
            timeout=60,
        )
    if response.status_code != 202:
        fail(f"POST /jobs returned {response.status_code}: {response.text}")

    job_id = response.json()["job_id"]
    for _ in range(120):  # wait up to 4 minutes
        job = requests.get(f"{BASE_URL}/jobs/{job_id}", timeout=10).json()
        if job["status"] == "done":
            return job["result"]
        if job["status"] == "failed":
            fail(f"job failed: {job['error']}")
        time.sleep(2)
    fail("the job did not finish within 4 minutes")


step(f"checking {BASE_URL}/health/ready")
ready = requests.get(f"{BASE_URL}/health/ready", timeout=10)
if ready.status_code != 200:
    fail(f"not ready: {ready.status_code} {ready.text}")

step("clean invoice (invoice_01.pdf) should pass without review")
result = run_job("samples/invoice_01.pdf", "application/pdf")
invoice = result["invoice"]
if invoice["vendor_name"] != "Apex Digital Solutions":
    fail(f"unexpected vendor: {invoice['vendor_name']}")
if invoice["total"] is None or abs(invoice["total"] - 731.6) > 0.01:
    fail(f"unexpected total: {invoice['total']}")
if result["needs_review"]:
    fail(f"expected no review, but problems were found: {result['problems']}")

step("cut-off invoice (invoice_04.png) should need review")
result = run_job("samples/invoice_04.png", "image/png")
if not result["needs_review"]:
    fail("expected this invoice to need review")

step("saving a corrected version")
corrected = dict(result["invoice"], tax_amount=111.6, total=731.6)
response = requests.post(
    f"{BASE_URL}/invoices",
    json={"file_name": "invoice_04.png", "original": result, "corrected": corrected},
    timeout=30,
)
if response.status_code != 200:
    fail(f"POST /invoices returned {response.status_code}: {response.text}")
saved = response.json()
if saved["remaining_problems"]:
    fail(f"corrected invoice still has problems: {saved['remaining_problems']}")

step("the saved invoice appears in the list")
saved_list = requests.get(f"{BASE_URL}/invoices", timeout=10).json()
if saved["id"] not in [record["id"] for record in saved_list]:
    fail("the saved invoice was not found in GET /invoices")

print("All checks passed.")