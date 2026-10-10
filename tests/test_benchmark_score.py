from benchmark.score import percent, same_number, same_text, score_invoice


def make_invoice(**changes):
    invoice = {
        "vendor_name": "Test Traders",
        "gstin": "29ABCDE1234F1Z5",
        "invoice_number": "INV-1",
        "invoice_date": "2024-01-05",
        "line_items": [{"description": "Pen", "quantity": 2.0, "unit_price": 5.0, "amount": 10.0}],
        "subtotal": 10.0,
        "tax_amount": 1.8,
        "total": 11.8,
    }
    invoice.update(changes)
    return invoice


def test_same_text_ignores_case_and_extra_spaces():
    assert same_text("Test  Traders", "test traders")
    assert not same_text("Test Traders", "Other Traders")


def test_none_only_matches_none():
    assert same_text(None, None)
    assert not same_text(None, "x")
    assert same_number(None, None)
    assert not same_number(None, 5)
    assert not same_number(5, None)


def test_same_number_allows_one_cent():
    assert same_number(10.0, 10.005)
    assert not same_number(10.0, 10.5)


def test_perfect_answer_scores_everything_correct():
    results, cells, wrong, invented, chances = score_invoice(make_invoice(), make_invoice())
    assert all(results.values())
    assert cells == (4, 4)
    assert wrong == []


def test_wrong_total_is_reported():
    results, cells, wrong, invented, chances = score_invoice(make_invoice(), make_invoice(total=99.0))
    assert results["total"] is False
    assert [item[0] for item in wrong] == ["total"]


def test_invented_value_is_counted():
    expected = make_invoice(total=None)
    got = make_invoice(total=11.8)
    results, cells, wrong, invented, chances = score_invoice(expected, got)
    assert invented == 1
    assert chances == 1


def test_extra_line_item_counts_as_wrong():
    got = make_invoice()
    got["line_items"] = got["line_items"] + [
        {"description": "Extra", "quantity": 1.0, "unit_price": 1.0, "amount": 1.0}
    ]
    results, cells, wrong, invented, chances = score_invoice(make_invoice(), got)
    assert results["line_items"] is False
    assert cells == (4, 8)

def test_percent_does_not_round_up_to_100():
    assert percent(526, 528) == "99.6%"
    assert percent(528, 528) == "100.0%"
    assert percent(0, 0) == "-"