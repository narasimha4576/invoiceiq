import json
import os

import pytest

from app.schemas import Invoice
from app.validators import validate_invoice

LABELS_PATH = os.path.join("benchmark", "labels.json")


def load_labels():
    with open(LABELS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_there_are_enough_labelled_invoices():
    assert len(load_labels()) >= 30


@pytest.mark.parametrize("label", load_labels(), ids=lambda label: label["file"])
def test_label_is_consistent_and_its_file_exists(label):
    assert os.path.exists(os.path.join("benchmark", "invoices", label["file"]))
    assert validate_invoice(Invoice(**label["invoice"])) == []