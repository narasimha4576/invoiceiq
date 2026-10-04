import os

from app.extractor import extract_with_confidence
from app.review import review_invoice

for name in sorted(os.listdir("samples")):
    if name.endswith((".pdf", ".png", ".jpg", ".jpeg")):
        result = review_invoice(extract_with_confidence(os.path.join("samples", name)))
        print("=====", name, "| needs_review:", result.needs_review)
        print("  low confidence:", result.low_confidence_fields)
        for p in result.problems:
            print("  problem:", p.field, "-", p.message)