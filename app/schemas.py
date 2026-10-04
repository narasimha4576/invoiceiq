from pydantic import BaseModel


class LineItem(BaseModel):
    description: str | None
    quantity: float | None
    unit_price: float | None
    amount: float | None


class Invoice(BaseModel):
    vendor_name: str | None
    gstin: str | None
    invoice_number: str | None
    invoice_date: str | None
    line_items: list[LineItem]
    subtotal: float | None
    tax_amount: float | None
    total: float | None


class Problem(BaseModel):
    field: str
    message: str


class FieldConfidence(BaseModel):
    vendor_name: float
    gstin: float
    invoice_number: float
    invoice_date: float
    line_items: float
    subtotal: float
    tax_amount: float
    total: float


class AIExtraction(BaseModel):
    invoice: Invoice
    confidence: FieldConfidence


class ReviewedInvoice(BaseModel):
    invoice: Invoice
    confidence: dict[str, float]
    problems: list[Problem]
    low_confidence_fields: list[str]
    needs_review: bool