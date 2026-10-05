import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

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
        # Keep the result so it stays on screen when the page refreshes
        st.session_state["result"] = response.json()
        st.session_state["file_name"] = uploaded.name
        st.session_state["file_bytes"] = uploaded.getvalue()
        st.session_state["file_type"] = uploaded.type
    else:
        st.error(f"The API returned an error ({response.status_code}): {response.text}")

result = st.session_state.get("result")

if result is not None:
    invoice = result["invoice"]
    confidence = result["confidence"]
    low_confidence = result["low_confidence_fields"]
    problems = result["problems"]

    left, right = st.columns(2)

    with left:
        st.subheader(st.session_state["file_name"])
        if st.session_state["file_type"].startswith("image/"):
            st.image(st.session_state["file_bytes"])
        else:
            st.info("A preview is only shown for images. This file is a PDF.")

    with right:
        if result["needs_review"]:
            st.warning("This invoice needs human review.")
        else:
            st.success("Looks good - no problems found.")

        rows = []
        field_names = [
            "vendor_name",
            "gstin",
            "invoice_number",
            "invoice_date",
            "subtotal",
            "tax_amount",
            "total",
        ]
        for name in field_names:
            value = invoice[name]
            has_problem = any(p["field"] == name for p in problems)
            needs_check = has_problem or name in low_confidence
            rows.append(
                {
                    "Field": name,
                    "Value": "-" if value is None else str(value),
                    "Confidence": f"{confidence[name]:.2f}",
                    "Status": "CHECK" if needs_check else "OK",
                }
            )
        st.table(rows)

        st.subheader("Line items")
        if invoice["line_items"]:
            st.dataframe(invoice["line_items"])
        else:
            st.write("No line items found.")

        if problems:
            st.subheader("Problems found")
            for p in problems:
                st.error(f"{p['field']}: {p['message']}")