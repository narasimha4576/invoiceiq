MODEL_NAME = "gemini-3.1-flash-lite"
# GST rates (in %) we treat as normal. Includes older rates, because invoices
# from before 22 Sept 2025 still use 12% and 28%.
ALLOWED_TAX_RATES = [0, 0.25, 3, 5, 12, 18, 28, 40]