from app.schemas import Invoice, Problem

# Allow tiny rounding differences (for example 0.005 cents)
TOLERANCE = 0.05


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


def validate_invoice(invoice: Invoice) -> list[Problem]:
    """Run all checks and return every problem found."""
    return check_line_items(invoice) + check_subtotal(invoice) + check_total(invoice)