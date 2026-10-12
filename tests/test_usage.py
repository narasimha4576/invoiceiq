from app import storage, usage


def use_temporary_database(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")


def test_allow_ai_call_stops_at_the_limit(tmp_path, monkeypatch):
    use_temporary_database(tmp_path, monkeypatch)
    assert usage.allow_ai_call(2) is True
    assert usage.allow_ai_call(2) is True
    assert usage.allow_ai_call(2) is False


def test_no_limit_always_allows(tmp_path, monkeypatch):
    use_temporary_database(tmp_path, monkeypatch)
    assert usage.allow_ai_call(0) is True
    assert usage.allow_ai_call(0) is True


def test_a_new_day_starts_a_new_count(tmp_path, monkeypatch):
    use_temporary_database(tmp_path, monkeypatch)
    monkeypatch.setattr(usage, "today", lambda: "2026-01-01")
    assert usage.allow_ai_call(1) is True
    assert usage.allow_ai_call(1) is False

    monkeypatch.setattr(usage, "today", lambda: "2026-01-02")
    assert usage.allow_ai_call(1) is True