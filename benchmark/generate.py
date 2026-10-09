"""Create a labelled set of fake invoices for measuring accuracy.

Run it from the project folder:
    python benchmark/generate.py

It writes invoice files to benchmark/invoices/ and the correct answers to
benchmark/labels.json. The same seed always gives the same invoices.
"""
import json
import os
import random
from datetime import date, timedelta

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SEED = 42
OUT_DIR = os.path.join("benchmark", "invoices")
LABELS_PATH = os.path.join("benchmark", "labels.json")

# (kind, how many, file type)
PLAN = [
    ("clean_pdf", 12, "pdf"),
    ("clean_png", 8, "png"),
    ("degraded_jpg", 8, "jpg"),
    ("cut_off_png", 8, "png"),
]

VENDORS = [
    "Sri Venkateswara Traders",
    "Kaveri Electronics",
    "Lakshmi Office Supplies",
    "Bharat Stationery Mart",
    "Tungabhadra Enterprises",
    "Maruthi Computers",
    "Annapurna Distributors",
    "Sai Krishna Agencies",
    "Nandi Tech Pvt Ltd",
    "Kohinoor Wholesale",
    "Blue Orchid Services LLP",
    "Green Leaf Traders",
    "Southern Star Supplies",
    "Rayalaseema Enterprises",
]

BUYERS = [
    "Sunrise Cafe",
    "Quantum Retailers",
    "Nexus Innovations Pvt Ltd",
    "Orchid Dental Clinic",
    "Pioneer Coaching Centre",
    "Metro Fitness Club",
    "Daily Fresh Mart",
    "Horizon Print Works",
]

# (name, lowest price, highest price)
ITEMS = [
    ("Wireless Mouse", 250, 900),
    ("Mechanical Keyboard", 1500, 6000),
    ("USB-C Cable", 120, 600),
    ("Laptop Stand", 600, 2500),
    ("Notebook (Pack of 5)", 150, 450),
    ("Printer Paper A4 (500 sheets)", 300, 550),
    ("Ballpoint Pens (Box)", 80, 250),
    ("Desk Lamp", 500, 2200),
    ("Office Chair", 3500, 9000),
    ("Monitor 24 inch", 7000, 14000),
    ("Webcam HD", 900, 3500),
    ("Headphones", 700, 4000),
    ("Power Strip", 250, 900),
    ("Whiteboard Markers (Set)", 120, 400),
    ("External Hard Drive 1TB", 3200, 6500),
    ("Cloud Hosting (Monthly)", 2000, 12000),
]

STATE_CODES = ["07", "09", "19", "24", "27", "29", "32", "33", "36", "37"]
DATE_STYLES = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]
PREFIXES = ["SV", "KE", "LO", "BM", "TE", "MC"]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def make_gstin(rng):
    """A made-up number with the right shape (not a real company's)."""
    return (
        rng.choice(STATE_CODES)
        + "".join(rng.choice(LETTERS) for _ in range(5))
        + "".join(str(rng.randint(0, 9)) for _ in range(4))
        + rng.choice(LETTERS)
        + str(rng.randint(1, 9))
        + "Z"
        + rng.choice("0123456789" + LETTERS)
    )


def make_invoice(rng, number):
    """Invent the data of one invoice. Returns the data and its tax lines."""
    items = []
    for name, low, high in rng.sample(ITEMS, rng.randint(1, 7)):
        quantity = rng.randint(1, 40)
        unit_price = round(rng.uniform(low, high), 2)
        items.append(
            {
                "description": name,
                "quantity": float(quantity),
                "unit_price": unit_price,
                "amount": round(quantity * unit_price, 2),
            }
        )

    subtotal = round(sum(item["amount"] for item in items), 2)
    tax_style = rng.choice(["gst5", "gst18", "cgst_sgst", "igst"])
    if tax_style == "gst5":
        tax_lines = [("GST (5%)", round(subtotal * 0.05, 2))]
    elif tax_style == "gst18":
        tax_lines = [("GST (18%)", round(subtotal * 0.18, 2))]
    elif tax_style == "igst":
        tax_lines = [("IGST (18%)", round(subtotal * 0.18, 2))]
    else:
        half = round(subtotal * 0.09, 2)
        tax_lines = [("CGST (9%)", half), ("SGST (9%)", half)]

    tax_amount = round(sum(amount for _, amount in tax_lines), 2)
    issued = date(2023, 1, 1) + timedelta(days=rng.randint(0, 1000))

    invoice = {
        "vendor_name": rng.choice(VENDORS),
        "gstin": make_gstin(rng),
        "invoice_number": f"INV-{rng.choice(PREFIXES)}-{1000 + number}",
        "invoice_date": issued.strftime(rng.choice(DATE_STYLES)),
        "line_items": items,
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total": round(subtotal + tax_amount, 2),
    }
    return invoice, tax_lines


def load_font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def render(invoice, tax_lines, buyer, show_totals):
    """Draw the invoice as an image."""
    width, height = 1240, 1754
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title = load_font(42)
    body = load_font(26)

    draw.text((80, 80), invoice["vendor_name"], font=title, fill="black")
    draw.text((80, 140), f"GSTIN: {invoice['gstin']}", font=body, fill="black")
    draw.text((780, 80), "TAX INVOICE", font=title, fill="black")
    draw.text((780, 140), f"Invoice No: {invoice['invoice_number']}", font=body, fill="black")
    draw.text((780, 180), f"Date: {invoice['invoice_date']}", font=body, fill="black")
    draw.text((80, 240), f"Bill To: {buyer}", font=body, fill="black")

    y = 320
    draw.rectangle([(60, y - 12), (1180, y + 40)], fill=(70, 90, 140))
    draw.text((80, y), "Item Description", font=body, fill="white")
    draw.text((780, y), "Qty", font=body, fill="white", anchor="ra")
    draw.text((960, y), "Rate (Rs.)", font=body, fill="white", anchor="ra")
    draw.text((1160, y), "Amount (Rs.)", font=body, fill="white", anchor="ra")

    y += 70
    for item in invoice["line_items"]:
        draw.text((80, y), item["description"], font=body, fill="black")
        draw.text((780, y), f"{item['quantity']:g}", font=body, fill="black", anchor="ra")
        draw.text((960, y), f"{item['unit_price']:,.2f}", font=body, fill="black", anchor="ra")
        draw.text((1160, y), f"{item['amount']:,.2f}", font=body, fill="black", anchor="ra")
        y += 50
        draw.line([(60, y - 8), (1180, y - 8)], fill=(190, 190, 190))
    y += 30

    if not show_totals:
        # The page ends before the totals, like a cut-off photo
        return image.crop((0, 0, width, y))

    totals = [("Subtotal", invoice["subtotal"])] + tax_lines + [("Grand Total", invoice["total"])]
    for label, value in totals:
        draw.text((800, y), label, font=body, fill="black")
        draw.text((1160, y), f"{value:,.2f}", font=body, fill="black", anchor="ra")
        y += 46
    return image


def degrade(image, rng):
    """Make the picture look like a poor phone photo."""
    image = image.rotate(rng.uniform(-3, 3), expand=True, fillcolor="white")
    image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.8, 1.6)))
    new_width = 800
    return image.resize((new_width, int(image.height * new_width / image.width)))


def main():
    rng = random.Random(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    labels = []
    number = 0
    for kind, count, file_type in PLAN:
        for _ in range(count):
            number += 1
            invoice, tax_lines = make_invoice(rng, number)
            buyer = rng.choice(BUYERS)
            file_name = f"inv_{number:03d}.{file_type}"
            path = os.path.join(OUT_DIR, file_name)

            image = render(invoice, tax_lines, buyer, show_totals=(kind != "cut_off_png"))
            truth = dict(invoice)

            if kind == "degraded_jpg":
                degrade(image, rng).save(path, quality=rng.randint(35, 55))
            elif kind == "clean_pdf":
                image.save(path, "PDF", resolution=150)
            else:
                image.save(path)

            if kind == "cut_off_png":
                # The totals are not on the page, so the right answer is "nothing"
                truth["subtotal"] = None
                truth["tax_amount"] = None
                truth["total"] = None

            labels.append({"file": file_name, "kind": kind, "invoice": truth})

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)
    print(f"Created {len(labels)} invoices in {OUT_DIR} and the answers in {LABELS_PATH}")


if __name__ == "__main__":
    main()