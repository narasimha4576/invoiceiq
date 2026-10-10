"""Compare the AI's saved answers with the correct answers and print a report.

Usage (from the project folder):
    python -m benchmark.score

Reads benchmark/results/predictions.json (made by benchmark.run) and writes
benchmark/results/report.md.
"""
import json
import os

LABELS_PATH = os.path.join("benchmark", "labels.json")
PREDICTIONS_PATH = os.path.join("benchmark", "results", "predictions.json")
REPORT_PATH = os.path.join("benchmark", "results", "report.md")

KINDS = ["clean_pdf", "clean_png", "degraded_jpg", "cut_off_png"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def same_text(expected, got):
    """Texts match if they are equal, ignoring capital letters and extra spaces."""
    if expected is None or got is None:
        return expected is None and got is None
    return " ".join(str(expected).split()).casefold() == " ".join(str(got).split()).casefold()


def same_number(expected, got):
    """Numbers match if they differ by one cent/paisa or less."""
    if expected is None or got is None:
        return expected is None and got is None
    return abs(float(expected) - float(got)) <= 0.01


FIELD_CHECKS = {
    "vendor_name": same_text,
    "gstin": same_text,
    "invoice_number": same_text,
    "invoice_date": same_text,
    "subtotal": same_number,
    "tax_amount": same_number,
    "total": same_number,
}

ITEM_CHECKS = {
    "description": same_text,
    "quantity": same_number,
    "unit_price": same_number,
    "amount": same_number,
}


def score_invoice(expected, got):
    """Compare one answer with the truth.

    Returns: per-field results, (correct, total) line item cells, a list of
    wrong fields, how many values were invented, and how many chances there were.
    """
    results = {}
    wrong = []
    invented = 0
    chances = 0

    for field, check in FIELD_CHECKS.items():
        ok = check(expected[field], got[field])
        results[field] = ok
        if not ok:
            wrong.append((field, expected[field], got[field]))
        if expected[field] is None:
            chances += 1
            if got[field] is not None:
                invented += 1  # the page shows nothing, but the AI gave a value

    expected_items = expected["line_items"]
    got_items = got["line_items"]
    correct_cells = 0
    total_cells = 0
    for index, item in enumerate(expected_items):
        got_item = got_items[index] if index < len(got_items) else {}
        for key, check in ITEM_CHECKS.items():
            total_cells += 1
            if check(item[key], got_item.get(key)):
                correct_cells += 1
    # Extra line items that should not be there count as wrong cells
    total_cells += 4 * max(0, len(got_items) - len(expected_items))

    results["line_items"] = correct_cells == total_cells
    if not results["line_items"]:
        wrong.append(
            ("line_items", f"{len(expected_items)} items", f"{correct_cells}/{total_cells} cells right")
        )
    return results, (correct_cells, total_cells), wrong, invented, chances


def collect():
    labels = {label["file"]: label for label in load_json(LABELS_PATH)}
    predictions = load_json(PREDICTIONS_PATH)

    fields = list(FIELD_CHECKS) + ["line_items"]
    summary = {
        "stats": {kind: {field: [0, 0] for field in fields} for kind in KINDS},
        "cells": {kind: [0, 0] for kind in KINDS},
        "cut_off": [0, 0],  # [flagged for review, total]
        "others": [0, 0],  # [flagged for review (false alarms), total]
        "invented": [0, 0],  # [invented values, chances to invent]
        "silent": [],
        "failed": [],
        "scored": 0,
        "planned": len(predictions),
    }

    for name, prediction in predictions.items():
        label = labels.get(name)
        if label is None:
            continue
        if "error" in prediction:
            summary["failed"].append((name, prediction["error"]))
            continue

        kind = label["kind"]
        results, item_cells, wrong, invented, chances = score_invoice(
            label["invoice"], prediction["invoice"]
        )
        summary["scored"] += 1
        for field, ok in results.items():
            summary["stats"][kind][field][0] += int(ok)
            summary["stats"][kind][field][1] += 1
        summary["cells"][kind][0] += item_cells[0]
        summary["cells"][kind][1] += item_cells[1]
        summary["invented"][0] += invented
        summary["invented"][1] += chances

        group = summary["cut_off"] if kind == "cut_off_png" else summary["others"]
        group[0] += int(prediction["needs_review"])
        group[1] += 1

        if wrong and not prediction["needs_review"]:
            summary["silent"].append((name, wrong))
    return summary


def percent(correct, total):
    return "-" if total == 0 else f"{100 * correct / total:.0f}%"


def table(headers, rows, markdown):
    if markdown:
        lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
        lines += ["| " + " | ".join(row) + " |" for row in rows]
        return "\n".join(lines)
    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]
    return "\n".join(
        "  ".join(str(cell).ljust(width) for cell, width in zip(row, widths))
        for row in [headers] + rows
    )


def build_report(summary, markdown):
    def heading(text):
        return f"\n## {text}\n" if markdown else f"\n{text}\n{'-' * len(text)}"

    lines = []
    failed = summary["failed"]
    lines.append(
        f"Invoices scored: {summary['scored']} of {summary['planned']}"
        + (f" ({len(failed)} AI calls failed)" if failed else "")
    )

    all_correct = sum(c for kind in KINDS for c, t in summary["stats"][kind].values())
    all_total = sum(t for kind in KINDS for c, t in summary["stats"][kind].values())
    lines.append(f"Overall: {all_correct}/{all_total} field checks correct ({percent(all_correct, all_total)})")

    lines.append(heading("Field accuracy (correct / total)"))
    headers = ["field"] + KINDS + ["all"]
    rows = []
    for field in summary["stats"][KINDS[0]]:
        row = [field]
        sum_c = sum_t = 0
        for kind in KINDS:
            c, t = summary["stats"][kind][field]
            row.append(f"{c}/{t}" if t else "-")
            sum_c += c
            sum_t += t
        row.append(f"{sum_c}/{sum_t} ({percent(sum_c, sum_t)})" if sum_t else "-")
        rows.append(row)

    cell_row = ["line item cells"]
    sum_c = sum_t = 0
    for kind in KINDS:
        c, t = summary["cells"][kind]
        cell_row.append(f"{c}/{t}" if t else "-")
        sum_c += c
        sum_t += t
    cell_row.append(f"{sum_c}/{sum_t} ({percent(sum_c, sum_t)})" if sum_t else "-")
    rows.append(cell_row)
    lines.append(table(headers, rows, markdown))

    lines.append(heading("Review flag"))
    flagged, total = summary["cut_off"]
    lines.append(f"Cut-off invoices flagged for review: {flagged}/{total}")
    flagged, total = summary["others"]
    lines.append(f"Other invoices flagged for review (false alarms): {flagged}/{total}")
    invented, chances = summary["invented"]
    lines.append(f"Invented values (a value given where the page shows nothing): {invented}/{chances}")
    silent = summary["silent"]
    lines.append(f"Wrong but NOT flagged for review (silent errors): {len(silent)} invoices")

    if silent:
        lines.append(heading("Silent errors (first 10)"))
        for name, wrong in silent[:10]:
            for field, expected, got in wrong:
                lines.append(f"- {name}: {field} expected {expected!r}, got {got!r}")

    if failed:
        lines.append(heading("Failed AI calls"))
        for name, error in failed:
            lines.append(f"- {name}: {error}")

    lines.append(heading("Note"))
    lines.append(
        "These invoices are generated: they share one layout, and the PDFs are pictures of invoices. "
        "Real invoices are messier, so real-world accuracy is likely lower."
    )
    return "\n".join(lines)


def main():
    if not os.path.exists(PREDICTIONS_PATH):
        print("No answers yet. Run: python -m benchmark.run")
        return

    summary = collect()
    print(build_report(summary, markdown=False))

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Benchmark report\n\n" + build_report(summary, markdown=True) + "\n")
    print(f"\nSaved {REPORT_PATH}")


if __name__ == "__main__":
    main()