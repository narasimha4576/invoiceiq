import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

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


st.set_page_config(page_title="InvoiceIQ", layout="wide")
st.title("InvoiceIQ - invoice review")

uploaded = st.file_uploader("Upload an invoice", type=["pdf", "png", "jpg", "jpeg"])

if uploaded is not None and st.button("Extract invoice"):
    with st.spinner("Reading the invoice..."):
        try:
            response = requests.post(
                f"{API_URL}/extract",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                timeout=120,
            )
        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the API. Is it running? Start it with: uvicorn app.main:app --reload")
            st.stop()

    if response.status_code == 200:
        st.session_state["result"] = response.json()
        st.session_state["file_name"] = uploaded.name
        st.session_state["file_bytes"] = uploaded.getvalue()
        st.session_state["file_type"] = uploaded.type
        # A new number for every extraction, so old edits do not carry over
        st.session_state["run_id"] = st.session_state.get("run_id", 0) + 1
        st.session_state.pop("saved", None)
    else:
        st.error(f"The API returned an error ({response.status_code}): {response.text}")

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
        if st.session_state["file_type"].startswith("image/"):
            st.image(st.session_state["file_bytes"])
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