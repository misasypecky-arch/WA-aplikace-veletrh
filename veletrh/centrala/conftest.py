import pytest

from app import webhooks
from app.store import subscriptions, votes


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Každý test začíná s prázdnými hlasy a odběry a bez čekání mezi pokusy o doručení."""
    votes.clear()
    subscriptions.clear()
    monkeypatch.setattr(webhooks, "RETRY_DELAYS", (0.0, 0.0, 0.0))
    yield
    votes.clear()
    subscriptions.clear()
