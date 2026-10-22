"""Rozesílání událostí: filtr podle patra, podpis, opakování a odolnost proti výpadku terminálu."""

import hashlib
import hmac
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import webhooks
from app.main import app
from app.store import subscriptions

client = TestClient(app)


@pytest.fixture
def inbox(monkeypatch):
    """Falešné terminály: zaznamenává požadavky a odpovídá podle handler_fn."""
    calls = []
    state = {"handler": lambda req, n: httpx.Response(200)}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return state["handler"](request, len([c for c in calls if c.url == request.url]))

    monkeypatch.setattr(webhooks, "make_client",
                        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return calls, state


def subscribe(url, floor):
    return client.post("/api/v1/subscriptions", json={"callback_url": url, "floor": floor}).json()


def vote(stand, user="anna.a", rating=5):
    return client.post(f"/api/v1/stands/{stand}/votes", json={"username": user, "rating": rating, "favorite": True})


def test_only_matching_floor_and_null_get_event(inbox):
    calls, _ = inbox
    subscribe("http://t2/webhooks/votes", 2)
    subscribe("http://t1/webhooks/votes", 1)
    subscribe("http://tall/webhooks/votes", None)
    assert vote("S201").status_code == 201
    assert sorted(c.url.host for c in calls) == ["t2", "tall"]


def test_signature_and_body(inbox):
    calls, _ = inbox
    sub = subscribe("http://t2/webhooks/votes", 2)
    vote("S201", "Žofie.N", 4)
    (req,) = calls
    body = req.content
    expected = "sha256=" + hmac.new(sub["secret"].encode(), body, hashlib.sha256).hexdigest()
    assert req.headers["x-signature"] == expected
    event = json.loads(body)
    assert req.headers["x-event-id"] == event["id"]
    assert event["type"] == "vote.created"
    assert event["data"] == {"stand_id": "S201", "title": "Rezervační systém pro školní učebny", "floor": 2,
                             "username": "Žofie.N", "rating": 4, "favorite": True}
    assert "Žofie.N".encode() in body  # kompaktní UTF-8 JSON, žádné \u escape


def test_retry_sends_identical_bytes_and_signature_then_succeeds(inbox):
    calls, state = inbox
    state["handler"] = lambda req, n: httpx.Response(200 if n >= 3 else 503)
    subscribe("http://t2/webhooks/votes", 2)
    vote("S201")
    assert len(calls) == 3
    assert len({c.content for c in calls}) == 1
    assert len({c.headers["x-signature"] for c in calls}) == 1
    assert len({c.headers["x-event-id"] for c in calls}) == 1


def test_gives_up_after_four_attempts_and_vote_is_still_saved(inbox):
    calls, state = inbox

    def boom(req, n):
        raise httpx.ConnectError("terminál je vypnutý")

    state["handler"] = boom
    subscribe("http://t2/webhooks/votes", 2)
    assert vote("S201").status_code == 201
    assert len(calls) == 4  # 1 pokus + opakování po 1 s, 2 s a 4 s
    assert client.get("/api/v1/stats", params={"floor": 2}).json()["total_votes"] == 1


def test_subscription_dropped_after_repeated_failures(inbox, monkeypatch):
    calls, state = inbox
    monkeypatch.setenv("MAX_DELIVERY_FAILURES", "2")
    state["handler"] = lambda req, n: httpx.Response(500)
    subscribe("http://t2/webhooks/votes", 2)
    vote("S201", "a.a"); assert len(subscriptions.all()) == 1
    vote("S201", "b.b"); assert subscriptions.all() == []


def test_success_resets_failure_counter(inbox, monkeypatch):
    calls, state = inbox
    monkeypatch.setenv("MAX_DELIVERY_FAILURES", "2")
    subscribe("http://t2/webhooks/votes", 2)
    state["handler"] = lambda req, n: httpx.Response(500)
    vote("S201", "a.a")
    state["handler"] = lambda req, n: httpx.Response(200)
    vote("S201", "b.b")
    state["handler"] = lambda req, n: httpx.Response(500)
    vote("S201", "c.c")
    assert len(subscriptions.all()) == 1


def test_event_ids_differ_between_votes(inbox):
    calls, _ = inbox
    subscribe("http://t2/webhooks/votes", 2)
    vote("S201", "a.a"); vote("S201", "b.b")
    assert len({c.headers["x-event-id"] for c in calls}) == 2


def test_snapshot_contains_vote_that_was_already_delivered(inbox):
    """Hlas s created_at <= generated_at je ve snapshotu (na tom stojí #10)."""
    calls, _ = inbox
    subscribe("http://t2/webhooks/votes", 2)
    vote("S201")
    created = json.loads(calls[0].content)["created_at"]
    snap = client.get("/api/v1/stats", params={"floor": 2}).json()
    assert created <= snap["generated_at"]
    assert snap["total_votes"] == 1


def test_slow_terminal_times_out_then_event_is_resent(monkeypatch):
    """Terminál odpovídá později než za limit: centrála ohlásí timeout a pošle stejnou událost znovu."""
    import asyncio

    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            await asyncio.sleep(0.5)  # "zaseklá Wi-Fi": odpověď nedorazí v limitu
        return httpx.Response(200)

    monkeypatch.setattr(webhooks, "DELIVERY_TIMEOUT", 0.1)
    monkeypatch.setattr(webhooks, "make_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    subscribe("http://t2/webhooks/votes", 2)
    assert vote("S201").status_code == 201
    assert len(calls) == 2
    assert calls[0].content == calls[1].content
    assert calls[0].headers["x-event-id"] == calls[1].headers["x-event-id"]
