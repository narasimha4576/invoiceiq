from app import storage


def test_save_and_list(tmp_path, monkeypatch):
    # Use a temporary database so the real one is not touched
    monkeypatch.setattr(storage, "DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")

    new_id = storage.save_invoice("a.pdf", {"x": 1}, {"x": 2}, True)
    rows = storage.list_invoices()

    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["original"] == {"x": 1}
    assert rows[0]["corrected"] == {"x": 2}
    assert rows[0]["needs_review"] is True

def test_job_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")

    job_id = storage.create_job("a.pdf")
    assert storage.get_job(job_id)["status"] == "queued"

    storage.update_job(job_id, "done", result={"x": 1})
    job = storage.get_job(job_id)
    assert job["status"] == "done"
    assert job["result"] == {"x": 1}
    assert job["finished_at"] is not None

    assert storage.get_job("does-not-exist") is None