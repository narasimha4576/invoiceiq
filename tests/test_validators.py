from app.schemas import Invoice, LineItem
from app.validators import (
    check_line_items,
    check_subtotal,
    check_total,
    validate_invoice,
)


def make_invoice(**changes) -> Invoice:
    """Build a correct invoice, then change only what a test needs."""
    data = dict(
        vendor_name="Test Traders",
        gstin=None,
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
    data.update(changes)
    return Invoice(**data)


# ---- line items ----
def test_line_items_correct():
    assert check_line_items(make_invoice()) == []


def test_line_items_wrong_amount():
    bad_items = [
        LineItem(description="Pen", quantity=10, unit_price=5, amount=60),
        LineItem(description="Book", quantity=2, unit_price=20, amount=40),
    ]
    problems = check_line_items(make_invoice(line_items=bad_items))
    assert len(problems) == 1
    assert problems[0].field == "line_items[1].amount"


def test_line_items_small_rounding_allowed():
    items = [LineItem(description="Pen", quantity=10, unit_price=5, amount=50.01)]
    assert check_line_items(make_invoice(line_items=items)) == []


# ---- subtotal ----
def test_subtotal_correct():
    assert check_subtotal(make_invoice()) == []


def test_subtotal_wrong():
    problems = check_subtotal(make_invoice(subtotal=100))
    assert len(problems) == 1
    assert problems[0].field == "subtotal"


def test_subtotal_skipped_when_amount_missing():
    items = [LineItem(description="Pen", quantity=10, unit_price=5, amount=None)]
    assert check_subtotal(make_invoice(line_items=items)) == []


# ---- total ----
def test_total_correct():
    assert check_total(make_invoice()) == []


def test_total_wrong():
    problems = check_total(make_invoice(total=110))
    assert len(problems) == 1
    assert problems[0].field == "total"


def test_total_skipped_when_values_missing():
    assert check_total(make_invoice(tax_amount=None, total=None)) == []


# ---- everything together ----
def test_validate_invoice_all_good():
    assert validate_invoice(make_invoice()) == []


def test_validate_invoice_finds_several_problems():
    problems = validate_invoice(make_invoice(subtotal=100, total=110))
    fields = [p.field for p in problems]
    assert "subtotal" in fields
    assert "total" in fields