"""Send the benchmark invoices through the real AI and save its answers.

Usage (from the project folder):
    python -m benchmark.run                          all invoices
    python -m benchmark.run --per-kind 2             only 2 invoices of each kind (a cheap test)
    python -m benchmark.run --kind phone_photo --redo   ask the AI again for one kind of invoice

Answers are saved in benchmark/results/predictions.json. Invoices that already
have an answer are skipped (unless you use --redo), so it is safe to run again
after a failure.
"""
import argparse
import json
import os
import time

from app.extractor import extract_with_confidence
from app.review import review_invoice

BENCH_DIR = "benchmark"
LABELS_PATH = os.path.join(BENCH_DIR, "labels.json")
INVOICE_DIR = os.path.join(BENCH_DIR, "invoices")
RESULTS_DIR = os.path.join(BENCH_DIR, "results")
PREDICTIONS_PATH = os.path.join(RESULTS_DIR, "predictions.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def choose(labels, per_kind, kind):
    """Keep only some invoices: one kind, and/or the first few of each kind."""
    if kind is not None:
        labels = [label for label in labels if label["kind"] == kind]
    if per_kind is None:
        return labels
    seen = {}
    chosen = []
    for label in labels:
        seen[label["kind"]] = seen.get(label["kind"], 0) + 1
        if seen[label["kind"]] <= per_kind:
            chosen.append(label)
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-kind", type=int, default=None, help="only this many invoices of each kind")
    parser.add_argument("--kind", default=None, help="only invoices of this kind, for example phone_photo")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds to wait between AI calls")
    parser.add_argument("--redo", action="store_true", help="ask the AI again even if an answer is saved")
    parser.add_argument("--redo-errors", action="store_true", help="try again the invoices that failed before")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    labels = choose(load_json(LABELS_PATH, []), args.per_kind, args.kind)
    predictions = load_json(PREDICTIONS_PATH, {})

    for number, label in enumerate(labels, start=1):
        name = label["file"]
        previous = predictions.get(name)
        already_done = (
            previous is not None
            and not args.redo
            and not (args.redo_errors and "error" in previous)
        )
        if already_done:
            print(f"[{number}/{len(labels)}] {name}: already done, skipping")
            continue

        print(f"[{number}/{len(labels)}] {name} ...", end=" ", flush=True)
        try:
            extraction = extract_with_confidence(os.path.join(INVOICE_DIR, name))
            predictions[name] = review_invoice(extraction).model_dump()
            print("done")
        except Exception as error:
            predictions[name] = {"error": type(error).__name__}
            print(f"failed ({type(error).__name__})")

        save_json(PREDICTIONS_PATH, predictions)  # saved after every invoice
        time.sleep(args.delay)  # be gentle with the free quota

    print(f"Saved answers in {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()