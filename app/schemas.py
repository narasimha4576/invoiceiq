from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class Invoice(BaseModel):
    vendor_name: str
    gstin: str | None = None
    invoice_number: str
    invoice_date: str
    line_items: list[LineItem]
    subtotal: float
    tax_amount: float
    total: float