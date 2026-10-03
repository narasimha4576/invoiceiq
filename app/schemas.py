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