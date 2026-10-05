from app import storage


def test_save_and_list(tmp_path, monkeypatch):
    # Use a temporary database so the real one is not touched
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "test.db"))

    new_id = storage.save_invoice("a.pdf", {"x": 1}, {"x": 2}, True)
    rows = storage.list_invoices()

    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["original"] == {"x": 1}
    assert rows[0]["corrected"] == {"x": 2}
    assert rows[0]["needs_review"] is True