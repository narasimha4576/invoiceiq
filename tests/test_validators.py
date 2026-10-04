from app.schemas import Invoice, LineItem
from app.validators import (
    check_date,
    check_gstin,
    check_line_items,
    check_subtotal,
    check_tax_rate,
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

    # ---- GSTIN ----
def test_gstin_valid():
    assert check_gstin(make_invoice(gstin="29ABCDE1234F1Z5")) == []


def test_gstin_missing_is_skipped():
    assert check_gstin(make_invoice(gstin=None)) == []


def test_gstin_too_short():
    problems = check_gstin(make_invoice(gstin="29ABCDE1234"))
    assert len(problems) == 1
    assert problems[0].field == "gstin"


def test_gstin_lowercase_is_accepted():
    assert check_gstin(make_invoice(gstin="29abcde1234f1z5")) == []


# ---- tax rate ----
def test_tax_rate_18_percent_ok():
    assert check_tax_rate(make_invoice()) == []


def test_tax_rate_5_percent_ok():
    assert check_tax_rate(make_invoice(tax_amount=4.5)) == []


def test_tax_rate_not_standard():
    problems = check_tax_rate(make_invoice(tax_amount=20))
    assert len(problems) == 1
    assert problems[0].field == "tax_amount"


def test_tax_rate_skipped_when_tax_missing():
    assert check_tax_rate(make_invoice(tax_amount=None)) == []


# ---- date ----
def test_date_valid_iso():
    assert check_date(make_invoice(invoice_date="2023-10-01")) == []


def test_date_valid_day_first():
    assert check_date(make_invoice(invoice_date="15/10/2023")) == []


def test_date_incomplete():
    problems = check_date(make_invoice(invoice_date="2023-1"))
    assert len(problems) == 1
    assert problems[0].field == "invoice_date"


def test_date_in_future():
    problems = check_date(make_invoice(invoice_date="2999-01-01"))
    assert len(problems) == 1
    assert "future" in problems[0].message


def test_date_missing_is_skipped():
    assert check_date(make_invoice(invoice_date=None)) == []