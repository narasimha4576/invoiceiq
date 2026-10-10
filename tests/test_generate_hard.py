from benchmark.generate_hard import indian_format


def test_indian_digit_grouping():
    assert indian_format(999.5) == "999.50"
    assert indian_format(12345) == "12,345.00"
    assert indian_format(123456) == "1,23,456.00"
    assert indian_format(1234567.8) == "12,34,567.80"