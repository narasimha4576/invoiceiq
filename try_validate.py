import os

from app.extractor import extract_invoice
from app.validators import validate_invoice

for name in sorted(os.listdir("samples")):
    if name.endswith((".pdf", ".png", ".jpg", ".jpeg")):
        invoice = extract_invoice(os.path.join("samples", name))
        problems = validate_invoice(invoice)
        print(name, "->", "OK" if not problems else problems)