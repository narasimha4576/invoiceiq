import httpx
import pytest

from app import extractor


class FakeModels:
    """A pretend AI that fails a few times before it answers."""

    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def generate_content(self, model, contents, config=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise httpx.ConnectError("network blip")
        return "answer"


class FakeClient:
    def __init__(self, failures):
        self.models = FakeModels(failures)


def test_network_blips_are_retried(monkeypatch):
    client = FakeClient(failures=2)
    monkeypatch.setattr(extractor, "_get_client", lambda: client)
    monkeypatch.setattr(extractor.time, "sleep", lambda seconds: None)

    assert extractor._call_model(["invoice"]) == "answer"
    assert client.models.calls == 3


def test_gives_up_after_three_tries(monkeypatch):
    client = FakeClient(failures=10)
    monkeypatch.setattr(extractor, "_get_client", lambda: client)
    monkeypatch.setattr(extractor.time, "sleep", lambda seconds: None)

    with pytest.raises(httpx.ConnectError):
        extractor._call_model(["invoice"])
    assert client.models.calls == 3