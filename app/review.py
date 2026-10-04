from app.config import FAILED_CHECK_CONFIDENCE, REQUIRED_FIELDS, REVIEW_THRESHOLD
from app.schemas import AIExtraction, Invoice, Problem, ReviewedInvoice
from app.validators import validate_invoice


def check_missing_fields(invoice: Invoice) -> list[Problem]:
    """Required fields must have a value, and there must be line items."""
    problems = []
    for name in REQUIRED_FIELDS:
        if getattr(invoice, name) is None:
            problems.append(Problem(field=name, message="value is missing or not readable"))
    if not invoice.line_items:
        problems.append(Problem(field="line_items", message="no line items found"))
    return problems


def review_invoice(extraction: AIExtraction) -> ReviewedInvoice:
    invoice = extraction.invoice
    problems = validate_invoice(invoice) + check_missing_fields(invoice)
    confidence = extraction.confidence.model_dump()

    # A field that failed a check can no longer be trusted
    for problem in problems:
        name = problem.field.split("[")[0]  # "line_items[1].amount" -> "line_items"
        if name in confidence:
            confidence[name] = min(confidence[name], FAILED_CHECK_CONFIDENCE)

    # Low confidence only matters for fields that actually have a value
    low_confidence = [
        name
        for name, value in confidence.items()
        if value < REVIEW_THRESHOLD and getattr(invoice, name) not in (None, [])
    ]

    return ReviewedInvoice(
        invoice=invoice,
        confidence=confidence,
        problems=problems,
        low_confidence_fields=low_confidence,
        needs_review=bool(problems) or bool(low_confidence),
    )