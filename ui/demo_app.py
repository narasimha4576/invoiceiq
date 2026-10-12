import json
import sys
from pathlib import Path

import streamlit as st

# Make the project folder importable, so the demo can reuse the project's own code
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.review import check_missing_fields  # noqa: E402
from app.schemas import Invoice, LineItem  # noqa: E402
from app.validators import validate_invoice  # noqa: E402
from benchmark.score import score_invoice  # noqa: E402

INVOICE_DIR = ROOT / "benchmark" / "invoices"
REPO_URL = "https://github.com/narasimha4576/invoiceiq"

FIELDS = [
    "vendor_name",
    "gstin",
    "invoice_number",
    "invoice_date",
    "subtotal",
    "tax_amount",
    "total",
]

KIND_TEXT = {
    "clean_png": "Clean image",
    "degraded_jpg": "Tilted, blurry, low-quality photo",
    "cut_off_png": "Page cut off before the totals",
    "phone_photo": "Phone photo: dark table, tilt, shadow, noise",
    "smudged": "Amounts and totals covered by a stain",
    "layout_b": "A different layout, Indian digit grouping",
}


@st.cache_data
def load_gallery():
    """Image invoices with their correct answers and the system's saved answers."""
    labels = json.loads((ROOT / "benchmark" / "labels.json").read_text(encoding="utf-8"))
    predictions = json.loads(
        (ROOT / "benchmark" / "results" / "predictions.json").read_text(encoding="utf-8")
    )
    items = []
    for label in labels:
        name = label["file"]
        prediction = predictions.get(name)
        if name.endswith(".pdf") or prediction is None or "error" in prediction:
            continue
        items.append(
            {"file": name, "kind": label["kind"], "truth": label["invoice"], "prediction": prediction}
        )
    return items


def show_value(value):
    return "(nothing)" if value is None else str(value)


def comparison_rows(truth, result):
    matches = score_invoice(truth, result["invoice"])[0]
    return [
        {
            "field": field,
            "correct answer": show_value(truth[field]),
            "system's answer": show_value(result["invoice"][field]),
            "confidence": f"{result['confidence'][field]:.2f}",
            "match": "yes" if matches[field] else "NO",
        }
        for field in FIELDS
    ]


def show_result(truth, result, title):
    st.subheader(title)
    if result["needs_review"]:
        st.warning("The system flagged this invoice for human review.")
    else:
        st.success("The system found no problems.")
    st.table(comparison_rows(truth, result))

    items = result["invoice"]["line_items"]
    items_ok = score_invoice(truth, result["invoice"])[0]["line_items"]
    st.caption(f"Line items: {len(items)} found, {'all correct' if items_ok else 'not all correct'}.")
    if items:
        st.dataframe(items)
    for problem in result["problems"]:
        st.error(f"{problem['field']}: {problem['message']}")


def show_playground():
    st.write(
        "These are the same rule checks the system runs on every AI answer. "
        "Change a number or a code and watch the checks react."
    )
    left, right = st.columns(2)
    quantity = left.number_input("Quantity", value=10.0)
    unit_price = left.number_input("Unit price", value=500.0)
    amount = left.number_input("Line amount", value=5000.0)
    subtotal = right.number_input("Subtotal", value=5000.0)
    tax_amount = right.number_input("Tax amount", value=900.0)
    total = right.number_input("Total", value=5900.0)
    gstin = st.text_input("GSTIN", value="29ABCDE1234F1Z5")
    invoice_date = st.text_input("Invoice date", value="2024-03-15")

    invoice = Invoice(
        vendor_name="Example Traders",
        gstin=gstin or None,
        invoice_number="INV-1",
        invoice_date=invoice_date or None,
        line_items=[
            LineItem(description="Item", quantity=quantity, unit_price=unit_price, amount=amount)
        ],
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
    )
    problems = validate_invoice(invoice) + check_missing_fields(invoice)
    if problems:
        st.warning("An invoice like this would be flagged for human review:")
        for problem in problems:
            st.error(f"{problem.field}: {problem.message}")
    else:
        st.success("All checks pass.")


st.set_page_config(page_title="InvoiceIQ demo", layout="wide")
st.title("InvoiceIQ: AI invoice reading with a human-review safety net")
st.caption("Every invoice here is generated. Nothing is a real invoice, and no AI is called on this page.")

gallery_tab, playground_tab, about_tab = st.tabs(
    ["Sample gallery", "Try the safety net", "About this demo"]
)

with gallery_tab:
    items = load_gallery()
    if not items:
        st.error("The sample data could not be loaded.")
        st.stop()

    kinds = ["all"] + sorted({entry["kind"] for entry in items})
    kind = st.selectbox(
        "Type of invoice",
        kinds,
        format_func=lambda k: "All types" if k == "all" else KIND_TEXT.get(k, k),
    )
    shown = [entry for entry in items if kind == "all" or entry["kind"] == kind]
    choice = st.selectbox("Invoice", [entry["file"] for entry in shown])
    item = next(entry for entry in shown if entry["file"] == choice)

    left, right = st.columns(2)
    with left:
        st.image(
            str(INVOICE_DIR / item["file"]),
            caption=f"{item['file']} ({KIND_TEXT.get(item['kind'], item['kind'])})",
        )
    with right:
        show_result(item["truth"], item["prediction"], "What the system answered")

with playground_tab:
    show_playground()

with about_tab:
    st.markdown(
        f"""
**What this is.** InvoiceIQ reads an invoice with a vision AI model and returns structured data with a
confidence score for every field. Plain code then checks the answer (arithmetic, GST number format, tax
rate, dates) and flags uncertain invoices for a human to review.

**What you see in the gallery.** The answers were produced by the real system in a benchmark run. The page
compares them with the known-correct answers. No AI is called while you browse, and no key is involved.

**How well does it work?** On 66 generated invoices in 7 conditions it got 526 of 528 field checks right
(99.6%), invented no values, and every error it made was flagged for review.

**Limits.** The invoices are generated, with two layouts. Real invoices (handwriting, stamps, several pages,
other languages) are not measured yet, so real-world accuracy is likely lower.

**Run the full system yourself** with your own AI key, using Docker. Source code, benchmark and
instructions: {REPO_URL}
"""
    )