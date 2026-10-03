import os

from app.extractor import extract_invoice

for name in sorted(os.listdir("samples")):
    if name.endswith((".pdf", ".png", ".jpg", ".jpeg")):
        print("=====", name)
        invoice = extract_invoice(os.path.join("samples", name))
        print(invoice.model_dump_json(indent=2))