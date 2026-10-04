import re
from datetime import date, datetime

from app.config import ALLOWED_TAX_RATES
from app.schemas import Invoice, Problem

# Allow tiny rounding differences (for example 0.005 cents)
TOLERANCE = 0.05
# Allow small differences when working out the tax percentage
RATE_TOLERANCE = 0.3

# 15 characters: 2 digits, 5 letters, 4 digits, 1 letter, 1 letter/digit, "Z", 1 letter/digit
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

# Date styles we accept (day first, as used in India)
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def check_line_items(invoice: Invoice) -> list[Problem]:
    """Each line: quantity x unit price must equal the amount."""
    problems = []
    for number, item in enumerate(invoice.line_items, start=1):
        if item.quantity is None or item.unit_price is None or item.amount is None:
            continue  # cannot check a line with missing values
        expected = item.quantity * item.unit_price
        if not _close(expected, item.amount):
            problems.append(
                Problem(
                    field=f"line_items[{number}].amount",
                    message=f"quantity x unit price is {expected:.2f} but amount is {item.amount:.2f}",
                )
            )
    return problems


def check_subtotal(invoice: Invoice) -> list[Problem]:
    """All line amounts added together must equal the subtotal."""
    amounts = [item.amount for item in invoice.line_items]
    if invoice.subtotal is None or not amounts or any(a is None for a in amounts):
        return []  # cannot check
    expected = sum(amounts)
    if not _close(expected, invoice.subtotal):
        return [
            Problem(
                field="subtotal",
                message=f"line amounts add up to {expected:.2f} but subtotal is {invoice.subtotal:.2f}",
            )
        ]
    return []


def check_total(invoice: Invoice) -> list[Problem]:
    """Subtotal + tax must equal the total."""
    if invoice.subtotal is None or invoice.tax_amount is None or invoice.total is None:
        return []  # cannot check
    expected = invoice.subtotal + invoice.tax_amount
    if not _close(expected, invoice.total):
        return [
            Problem(
                field="total",
                message=f"subtotal + tax is {expected:.2f} but total is {invoice.total:.2f}",
            )
        ]
    return []


def check_gstin(invoice: Invoice) -> list[Problem]:
    """The GSTIN must have the right shape (15 characters)."""
    if invoice.gstin is None:
        return []  # cannot check
    cleaned = invoice.gstin.strip().upper()
    if not GSTIN_PATTERN.match(cleaned):
        return [
            Problem(
                field="gstin",
                message=f"'{invoice.gstin}' is not a valid GSTIN format (expected 15 characters, like 29ABCDE1234F1Z5)",
            )
        ]
    return []


def check_tax_rate(invoice: Invoice) -> list[Problem]:
    """Tax divided by subtotal should be a normal GST percentage."""
    if invoice.subtotal is None or invoice.tax_amount is None or invoice.subtotal <= 0:
        return []  # cannot check
    rate = invoice.tax_amount / invoice.subtotal * 100
    if any(abs(rate - allowed) <= RATE_TOLERANCE for allowed in ALLOWED_TAX_RATES):
        return []
    return [
        Problem(
            field="tax_amount",
            message=f"tax is {rate:.2f}% of the subtotal, which is not a standard GST rate",
        )
    ]


def _parse_date(text: str) -> date | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def check_date(invoice: Invoice) -> list[Problem]:
    """The date must be complete, real and not in the future."""
    if invoice.invoice_date is None:
        return []  # cannot check
    parsed = _parse_date(invoice.invoice_date)
    if parsed is None:
        return [
            Problem(
                field="invoice_date",
                message=f"'{invoice.invoice_date}' is not a complete, valid date",
            )
        ]
    if parsed > date.today():
        return [
            Problem(
                field="invoice_date",
                message=f"date {parsed} is in the future",
            )
        ]
    return []


def validate_invoice(invoice: Invoice) -> list[Problem]:
    """Run all checks and return every problem found."""
    return (
        check_line_items(invoice)
        + check_subtotal(invoice)
        + check_total(invoice)
        + check_gstin(invoice)
        + check_tax_rate(invoice)
        + check_date(invoice)
    )