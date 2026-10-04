MODEL_NAME = "gemini-3.1-flash-lite"
# GST rates (in %) we treat as normal. Includes older rates, because invoices
# from before 22 Sept 2025 still use 12% and 28%.
ALLOWED_TAX_RATES = [0, 0.25, 3, 5, 12, 18, 28, 40]
# An invoice needs a human review if any field's confidence is below this
REVIEW_THRESHOLD = 0.8
# When a field fails a check, its confidence is lowered to at most this
FAILED_CHECK_CONFIDENCE = 0.3
# Fields that must have a value, or the invoice needs review
REQUIRED_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "subtotal", "total"]