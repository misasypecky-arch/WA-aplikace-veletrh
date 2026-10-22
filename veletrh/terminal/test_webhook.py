import json

from fastapi.testclient import TestClient

from app import signature
from app.main import app
from conftest import SECRET

client = TestClient(app)


def event(event_id="evt_1", stand="S201", rating=5, favorite=True, floor=2, created_at="2026-10-22T09:00:00.000000Z"):
    return {"id": event_id, "type": "vote.created", "created_at": created_at,
            "data": {"stand_id": stand, "title": "Rezervační systém", "floor": floor,
                     "username": "Žofie.N", "rating": rating, "favorite": favorite}}


def post(payload, secret=SECRET, event_id=None, signature_header="auto", raw=None):
    body = raw if raw is not None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json", "X-Event-Id": event_id or payload["id"]}
    if signature_header == "auto":
        headers["X-Signature"] = signature.compute(secret, body)
    elif signature_header is not None:
        headers["X-Signature"] = signature_header
    return client.post("/webhooks/votes", content=body, headers=headers)


def stands():
    return {s["stand_id"]: s for s in client.get("/stats").json()["stands"]}


def test_docs_available():
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


# ---------------------------------------------------------------- #08 podpisy


def test_valid_signature_counts_vote():
    assert post(event()).status_code == 200
    s = stands()["S201"]
    assert s["votes"] == 1 and s["avg_rating"] == 5.0 and s["favorites"] == 1


def test_invalid_signature_is_401_and_not_counted():
    r = post(event(), signature_header="sha256=" + "0" * 64)
    assert r.status_code == 401
    assert client.get("/stats").json()["total_votes"] == 0


def test_missing_signature_is_401():
    assert post(event(), signature_header=None).status_code == 401
    assert client.get("/stats").json()["total_votes"] == 0


def test_signature_with_wrong_secret_is_401():
    assert post(event(), secret="jiny-secret").status_code == 401


def test_signature_is_over_raw_bytes_not_over_equal_json():
    """Stejný JSON, jiné bajty (mezery): podpis kompaktního zápisu nesmí platit pro hezky formátovaný."""
    payload = event()
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    pretty = json.dumps(payload, ensure_ascii=False, indent=2).encode()
    headers = {"Content-Type": "application/json", "X-Event-Id": "evt_1",
               "X-Signature": signature.compute(SECRET, compact)}
    assert client.post("/webhooks/votes", content=pretty, headers=headers).status_code == 401
    assert client.post("/webhooks/votes", content=compact, headers=headers).status_code == 200


def test_bare_hex_signature_is_accepted():
    body = json.dumps(event()).encode()
    bare = signature.compute(SECRET, body).removeprefix("sha256=")
    assert post(None, raw=body, event_id="evt_1", signature_header=bare).status_code == 200


def test_not_subscribed_yet_is_503():
    from app import main
    main.session.secret = None
    assert post(event(), signature_header="x").status_code == 503


# --------------------------------------------------------------- #09 idempotence


def test_duplicate_event_id_is_200_and_counted_once():
    for _ in range(3):
        assert post(event()).status_code == 200
    assert stands()["S201"]["votes"] == 1


def test_same_id_in_header_wins_and_different_ids_count_separately():
    post(event("evt_a")); post(event("evt_b", rating=3))
    s = stands()["S201"]
    assert s["votes"] == 2 and s["avg_rating"] == 4.0


def test_seen_ids_memory_is_bounded(monkeypatch):
    from app import main, store
    monkeypatch.setattr(store, "MAX_SEEN", 3)
    for i in range(5):
        post(event(f"evt_{i}"))
    assert len(main.store._seen) == 3
    assert stands()["S201"]["votes"] == 5


# ------------------------------------------------------------ #07 patra a tvar


def test_vote_from_other_floor_is_ignored():
    r = post(event(floor=1, stand="S101"))
    assert r.status_code == 200 and r.json()["status"] == "ignored"
    assert client.get("/stats").json()["total_votes"] == 0


def test_flat_event_shape_is_accepted():
    flat = {"stand_id": "S202", "rating": 4, "favorite": False}
    assert post(flat, event_id="evt_flat").status_code == 200
    assert stands()["S202"]["votes"] == 1


def test_invalid_body_after_valid_signature_is_422():
    assert post(None, raw=b"not json", event_id="e1").status_code == 422
    assert post({"id": "e2", "type": "vote.created", "data": {"stand_id": "S201", "rating": 9}}).status_code == 422
    assert client.get("/stats").json()["total_votes"] == 0


def test_unknown_event_type_is_ignored():
    e = event(); e["type"] = "something.else"
    assert post(e).json()["status"] == "ignored"


# ------------------------------------------------------------------ #05 zobrazení


def test_stats_sorted_by_average_with_expected_shape():
    post(event("e1", stand="S201", rating=3)); post(event("e2", stand="S202", rating=5)); post(event("e3", stand="S202", rating=4))
    d = client.get("/stats").json()
    assert set(d) == {"floor", "total_votes", "stands"} and d["floor"] == 2 and d["total_votes"] == 3
    assert [s["stand_id"] for s in d["stands"]] == ["S202", "S201"]
    assert set(d["stands"][0]) == {"stand_id", "title", "votes", "avg_rating", "favorites"}
    assert d["stands"][0]["avg_rating"] == 4.5


def test_screen_served():
    r = client.get("/")
    assert r.status_code == 200 and "/stats" in r.text
