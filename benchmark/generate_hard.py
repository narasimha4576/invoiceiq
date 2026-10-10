"""Add harder invoices to the benchmark.

Run it from the project folder, after benchmark/generate.py:
    python -m benchmark.generate_hard

New kinds of invoice:
    phone_photo  a quick, badly lit photo on a dark table (tilt, keystone, shadow, noise, blur)
    smudged      the amount column and the totals are covered (the right answer is "nothing")
    layout_b     a different layout, Indian digit grouping (1,23,456.00) and "Rs." prefixes
"""
import json
import os
import random

import numpy
from PIL import Image, ImageDraw, ImageFilter

from benchmark.generate import BUYERS, LABELS_PATH, OUT_DIR, load_font, make_invoice, render

SEED = 7

# (kind, how many, file type)
PLAN_HARD = [
    ("phone_photo", 12, "jpg"),
    ("smudged", 8, "png"),
    ("layout_b", 10, "png"),
]
HARD_KINDS = [kind for kind, _, _ in PLAN_HARD]


def indian_format(value):
    """1234567.5 -> '12,34,567.50' (the way many Indian invoices group digits)."""
    whole, fraction = f"{value:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{whole}.{fraction}"


def perspective_coefficients(output_corners, source_corners):
    """The 8 numbers PIL needs to squeeze a picture into a four-cornered shape."""
    rows = []
    for (x, y), (u, v) in zip(output_corners, source_corners):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    solution = numpy.linalg.solve(
        numpy.array(rows, dtype=float),
        numpy.array(source_corners, dtype=float).reshape(8),
    )
    return solution.tolist()


def phone_photo(page, rng):
    """Make a page look like a quick phone photo on a dark table."""
    table = (60, 55, 50)
    page = page.resize((1000, int(page.height * 1000 / page.width)))
    image = Image.new("RGB", (page.width + 200, page.height + 200), table)
    image.paste(page, (100, 100))
    image = image.rotate(rng.uniform(-5, 5), expand=True, fillcolor=table)

    # Keystone: the top edge looks narrower than the bottom edge
    width, height = image.size
    shift = int(width * rng.uniform(0.03, 0.07))
    coefficients = perspective_coefficients(
        [(shift, 0), (width - shift, 0), (width, height), (0, height)],
        [(0, 0), (width, 0), (width, height), (0, height)],
    )
    image = image.transform(
        image.size,
        Image.Transform.PERSPECTIVE,
        coefficients,
        Image.Resampling.BICUBIC,
        fillcolor=table,
    )

    # Uneven light: one side of the photo is darker
    strength = rng.uniform(0.3, 0.55)
    gradient = Image.linear_gradient("L").rotate(rng.choice([0, 90, 180, 270])).resize(image.size)
    shadow_mask = gradient.point(lambda value: int(value * strength))
    image = Image.composite(Image.new("RGB", image.size, (0, 0, 0)), image, shadow_mask)

    # Camera noise and blur
    noise = Image.effect_noise(image.size, 40).convert("RGB")
    image = Image.blend(image, noise, 0.08)
    image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.8, 1.4)))
    return image.resize((900, int(image.height * 900 / image.width)))


def smudge(image):
    """Cover the amount column and the totals, like a stain or a torn corner."""
    draw = ImageDraw.Draw(image)
    # The Rate column ends at x=960, so everything to the right of x=1000 is covered
    draw.rectangle([(1000, 300), (image.width, image.height)], fill=(235, 225, 205))
    return image


def render_b(invoice, tax_lines, buyer, rng):
    """A second layout: boxed header, HSN column, Indian digit grouping."""
    width, height = 1240, 1754
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title, body = load_font(38), load_font(25)

    draw.rectangle([(50, 50), (1190, 230)], outline=(40, 40, 40), width=3)
    draw.text((70, 65), invoice["vendor_name"].upper(), font=title, fill="black")
    draw.text((70, 125), f"GSTIN/UIN : {invoice['gstin']}", font=body, fill="black")
    draw.text((70, 170), f"Billed to : {buyer}", font=body, fill="black")
    draw.text((760, 125), f"Inv. No. : {invoice['invoice_number']}", font=body, fill="black")
    draw.text((760, 170), f"Dated : {invoice['invoice_date']}", font=body, fill="black")

    y = 270
    columns = [
        ("S.No", 70, "la"),
        ("Description of Goods", 140, "la"),
        ("HSN", 730, "la"),
        ("Qty", 910, "ra"),
        ("Rate", 1040, "ra"),
        ("Amount", 1170, "ra"),
    ]
    draw.rectangle([(50, y - 10), (1190, y + 42)], outline=(40, 40, 40), width=2)
    for text, x, anchor in columns:
        draw.text((x, y), text, font=body, fill="black", anchor=anchor)

    y += 60
    for number, item in enumerate(invoice["line_items"], start=1):
        hsn = str(rng.choice([8471, 8473, 4820, 9405, 8528, 8517, 3926]))
        draw.text((70, y), str(number), font=body, fill="black")
        draw.text((140, y), item["description"], font=body, fill="black")
        draw.text((730, y), hsn, font=body, fill="black")
        draw.text((910, y), f"{item['quantity']:g} Nos", font=body, fill="black", anchor="ra")
        draw.text((1040, y), indian_format(item["unit_price"]), font=body, fill="black", anchor="ra")
        draw.text((1170, y), indian_format(item["amount"]), font=body, fill="black", anchor="ra")
        y += 52
    draw.line([(50, y), (1190, y)], fill=(40, 40, 40), width=2)

    y += 25
    totals = [("Sub Total", invoice["subtotal"])] + tax_lines + [("Total Amount Payable", invoice["total"])]
    for label, value in totals:
        draw.text((620, y), label, font=body, fill="black")
        draw.text((1170, y), "Rs. " + indian_format(value), font=body, fill="black", anchor="ra")
        y += 46
    return image


def main():
    rng = random.Random(SEED)

    with open(LABELS_PATH, encoding="utf-8") as f:
        # Keep the original invoices, drop any earlier hard ones (so this can be run again)
        labels = [label for label in json.load(f) if label["kind"] not in HARD_KINDS]
    number = len(labels)

    for kind, count, file_type in PLAN_HARD:
        for _ in range(count):
            number += 1
            invoice, tax_lines = make_invoice(rng, number)
            buyer = rng.choice(BUYERS)
            file_name = f"inv_{number:03d}.{file_type}"
            path = os.path.join(OUT_DIR, file_name)
            truth = dict(invoice)

            if kind == "phone_photo":
                page = render(invoice, tax_lines, buyer, show_totals=True)
                phone_photo(page, rng).save(path, quality=rng.randint(30, 45))
            elif kind == "smudged":
                page = render(invoice, tax_lines, buyer, show_totals=True)
                smudge(page).save(path)
                # The covered values cannot be read, so the right answer is "nothing"
                truth["line_items"] = [dict(item, amount=None) for item in invoice["line_items"]]
                truth["subtotal"] = None
                truth["tax_amount"] = None
                truth["total"] = None
            else:
                render_b(invoice, tax_lines, buyer, rng).save(path)

            labels.append({"file": file_name, "kind": kind, "invoice": truth})

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)
    print(f"Now {len(labels)} labelled invoices in {OUT_DIR}")


if __name__ == "__main__":
    main()