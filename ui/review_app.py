import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

TEXT_FIELDS = ["vendor_name", "gstin", "invoice_number", "invoice_date"]
NUMBER_FIELDS = ["subtotal", "tax_amount", "total"]
ITEM_TEXT = ["description"]
ITEM_NUMBERS = ["quantity", "unit_price", "amount"]


def to_number(text: str):
    """Turn typed text into a number. Empty text means 'no value' (None)."""
    text = text.strip().replace(",", "")
    if text == "":
        return None
    return float(text)  # raises ValueError if it is not a number


def clean_cell(value):
    """Make a table cell safe to send: empty cells become None."""
    if value is None or value != value:  # NaN is the only value that is not equal to itself
        return None
    return value


def load_result(result, file_name, file_bytes, file_type):
    """Put a finished result on the screen."""
    st.session_state["result"] = result
    st.session_state["file_name"] = file_name
    st.session_state["file_bytes"] = file_bytes
    st.session_state["file_type"] = file_type or ""
    # A new number for every result, so old edits do not carry over
    st.session_state["run_id"] = st.session_state.get("run_id", 0) + 1
    st.session_state.pop("saved", None)


def fetch_jobs():
    """The most recent jobs, or None if the API cannot be reached."""
    try:
        response = requests.get(f"{API_URL}/jobs", params={"limit": 15}, timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return None


def wait_for_job(job_id: str, status_box, timeout_seconds: int = 240):
    """Check the job every 2 seconds until it is finished."""
    waited = 0
    while waited < timeout_seconds:
        response = requests.get(f"{API_URL}/jobs/{job_id}", timeout=10)
        if response.status_code != 200:
            return None, f"Could not read the job ({response.status_code})."
        job = response.json()
        if job["status"] in ("done", "failed"):
            return job, None
        status_box.info(f"Job status: {job['status']} ... ({waited} seconds)")
        time.sleep(2)
        waited += 2
    return None, "Still waiting after 4 minutes. Check the recent jobs list later."


st.set_page_config(page_title="InvoiceIQ", layout="wide")
st.title("InvoiceIQ - invoice review")

# ---- Sidebar: recent jobs ----
with st.sidebar:
    st.header("Recent jobs")
    st.button("Refresh list")  # any click re-runs the page and reloads the list
    recent = fetch_jobs()
    if recent is None:
        st.caption("Cannot reach the API.")
    elif not recent:
        st.caption("No jobs yet.")
    else:
        st.dataframe(
            [
                {
                    "file": j["file_name"],
                    "status": j["status"],
                    "needs review": {True: "yes", False: "no"}.get(j["needs_review"], "-"),
                }
                for j in recent
            ]
        )
        finished = {
            f"{j['file_name']} ({j['job_id'][:8]})": j["job_id"]
            for j in recent
            if j["status"] == "done"
        }
        if finished:
            choice = st.selectbox("Open a finished job", list(finished))
            if st.button("Open"):
                response = requests.get(f"{API_URL}/jobs/{finished[choice]}", timeout=10)
                if response.status_code == 200:
                    job = response.json()
                    load_result(job["result"], job["file_name"], None, "")
                else:
                    st.error("Could not open that job.")

# ---- Upload and wait for the result ----
uploaded = st.file_uploader("Upload an invoice", type=["pdf", "png", "jpg", "jpeg"])

if uploaded is not None and st.button("Extract invoice"):
    status_box = st.empty()
    try:
        response = requests.post(
            f"{API_URL}/jobs",
            files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is it running? Start it with: docker compose up")
        st.stop()

    if response.status_code != 202:
        st.error(f"The API returned an error ({response.status_code}): {response.text}")
        st.stop()

    job_id = response.json()["job_id"]
    status_box.info("Invoice sent. Waiting for the worker...")
    try:
        job, problem = wait_for_job(job_id, status_box)
    except requests.exceptions.RequestException:
        job, problem = None, "Lost the connection to the API while waiting."
    status_box.empty()

    if problem:
        st.error(problem)
    elif job["status"] == "failed":
        st.error(f"The job failed: {job['error']}")
    else:
        load_result(job["result"], uploaded.name, uploaded.getvalue(), uploaded.type)

# ---- Show the result and let a person correct it ----
result = st.session_state.get("result")

if result is not None:
    invoice = result["invoice"]
    confidence = result["confidence"]
    low_confidence = result["low_confidence_fields"]
    problems = result["problems"]
    run_id = st.session_state["run_id"]

    left, right = st.columns(2)

    with left:
        st.subheader(st.session_state["file_name"])
        file_bytes = st.session_state.get("file_bytes")
        if file_bytes is None:
            st.info("No preview: the uploaded file is deleted after processing.")
        elif st.session_state["file_type"].startswith("image/"):
            st.image(file_bytes)
        else:
            st.info("A preview is only shown for images. This file is a PDF.")

    with right:
        if result["needs_review"]:
            st.warning("This invoice needs human review. Fields marked with a warning sign need a look.")
        else:
            st.success("Looks good - no problems found. You can still correct anything below.")

        st.subheader("Fields")
        typed = {}
        for name in TEXT_FIELDS + NUMBER_FIELDS:
            value = invoice[name]
            messages = [p["message"] for p in problems if p["field"] == name]
            flagged = bool(messages) or name in low_confidence
            label = f"{name} (confidence {confidence[name]:.2f})"
            if flagged:
                label = ":warning: " + label
            typed[name] = st.text_input(
                label,
                value="" if value is None else str(value),
                help=" | ".join(messages) if messages else None,
                key=f"{name}_{run_id}",
            )

        st.subheader("Line items")
        item_messages = [p["message"] for p in problems if p["field"].startswith("line_items")]
        if item_messages or "line_items" in low_confidence:
            st.warning(
                f":warning: line items need a look (confidence {confidence['line_items']:.2f}). "
                + " | ".join(item_messages)
            )
        items = invoice["line_items"] or [
            {"description": "", "quantity": None, "unit_price": None, "amount": None}
        ]
        edited_items = st.data_editor(items, num_rows="dynamic", key=f"items_{run_id}")

        if problems:
            st.subheader("Problems found by the checks")
            for p in problems:
                st.error(f"{p['field']}: {p['message']}")

        if st.button("Save corrected invoice"):
            try:
                corrected = {name: (typed[name].strip() or None) for name in TEXT_FIELDS}
                for name in NUMBER_FIELDS:
                    corrected[name] = to_number(typed[name])
            except ValueError:
                st.error("subtotal, tax_amount and total must be plain numbers (or left empty).")
                st.stop()

            corrected_items = []
            for row in edited_items:
                cells = {key: clean_cell(row.get(key)) for key in ITEM_TEXT + ITEM_NUMBERS}
                if all(v is None or v == "" for v in cells.values()):
                    continue  # skip empty rows
                for key in ITEM_NUMBERS:
                    if cells[key] is not None:
                        cells[key] = float(cells[key])
                corrected_items.append(cells)
            corrected["line_items"] = corrected_items

            try:
                save_response = requests.post(
                    f"{API_URL}/invoices",
                    json={
                        "file_name": st.session_state["file_name"],
                        "original": result,
                        "corrected": corrected,
                    },
                    timeout=30,
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Is it running?")
                st.stop()

            if save_response.status_code == 200:
                st.session_state["saved"] = save_response.json()
            else:
                st.error(f"Could not save ({save_response.status_code}): {save_response.text}")

        saved = st.session_state.get("saved")
        if saved is not None:
            st.success(
                f"Saved as record #{saved['id']}. Both the AI's original answer and your corrected version are stored."
            )
            if saved["remaining_problems"]:
                st.warning("The corrected invoice still has problems:")
                for p in saved["remaining_problems"]:
                    st.write(f"- {p['field']}: {p['message']}")
            else:
                st.info("The corrected invoice passes all checks.")