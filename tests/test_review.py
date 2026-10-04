from app.review import check_missing_fields, review_invoice
from app.schemas import AIExtraction, FieldConfidence, Invoice, LineItem


def make_extraction(invoice_changes=None, confidence_changes=None) -> AIExtraction:
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
    invoice.update(invoice_changes or {})

    confidence = dict(
        vendor_name=1.0,
        gstin=1.0,
        invoice_number=1.0,
        invoice_date=1.0,
        line_items=1.0,
        subtotal=1.0,
        tax_amount=1.0,
        total=1.0,
    )
    confidence.update(confidence_changes or {})

    return AIExtraction(invoice=Invoice(**invoice), confidence=FieldConfidence(**confidence))


def test_clean_invoice_needs_no_review():
    result = review_invoice(make_extraction())
    assert result.needs_review is False
    assert result.problems == []
    assert result.low_confidence_fields == []


def test_low_confidence_triggers_review():
    result = review_invoice(make_extraction(confidence_changes={"invoice_number": 0.5}))
    assert result.needs_review is True
    assert "invoice_number" in result.low_confidence_fields


def test_failed_check_lowers_confidence():
    result = review_invoice(make_extraction(invoice_changes={"total": 110}))
    assert result.needs_review is True
    assert result.confidence["total"] <= 0.3
    assert "total" in [p.field for p in result.problems]


def test_missing_required_field_triggers_review():
    result = review_invoice(
        make_extraction(invoice_changes={"invoice_date": None}, confidence_changes={"invoice_date": 0.0})
    )
    assert result.needs_review is True
    assert "invoice_date" in [p.field for p in result.problems]


def test_missing_optional_field_is_fine():
    result = review_invoice(
        make_extraction(invoice_changes={"gstin": None}, confidence_changes={"gstin": 0.0})
    )
    assert result.needs_review is False


def test_line_item_problem_lowers_line_items_confidence():
    bad_items = [
        LineItem(description="Pen", quantity=10, unit_price=5, amount=60),
        LineItem(description="Book", quantity=2, unit_price=20, amount=40),
    ]
    result = review_invoice(make_extraction(invoice_changes={"line_items": bad_items}))
    assert result.confidence["line_items"] <= 0.3
    assert result.needs_review is True


def test_check_missing_fields_no_line_items():
    extraction = make_extraction(invoice_changes={"line_items": []})
    problems = check_missing_fields(extraction.invoice)
    assert "line_items" in [p.field for p in problems]