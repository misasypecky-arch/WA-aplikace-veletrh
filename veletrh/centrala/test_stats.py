from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def vote(stand, user, rating, fav=False):
    assert client.post(f"/api/v1/stands/{stand}/votes",
                       json={"username": user, "rating": rating, "favorite": fav}).status_code == 201


def test_empty_stats_lists_all_stands_with_zero():
    d = client.get("/api/v1/stats").json()
    assert d["total_votes"] == 0 and len(d["stands"]) >= 8
    assert all(s["votes"] == 0 and s["avg_rating"] == 0.0 for s in d["stands"])


def test_stats_example_from_assignment():
    vote("S201", "anna.a", 5, True)
    vote("S201", "bob.b", 4)
    vote("S202", "anna.a", 3)
    d = client.get("/api/v1/stats", params={"floor": 2}).json()
    s201 = next(s for s in d["stands"] if s["stand_id"] == "S201")
    assert s201 == {"stand_id": "S201", "title": "Rezervační systém pro školní učebny", "floor": 2,
                    "votes": 2, "rating_sum": 9, "avg_rating": 4.5, "favorites": 1}
    assert d["total_votes"] == 3
    assert {s["floor"] for s in d["stands"]} == {2}


def test_floor_filter_and_empty_floor():
    vote("S101", "anna.a", 5)
    assert client.get("/api/v1/stats", params={"floor": 2}).json()["total_votes"] == 0
    assert client.get("/api/v1/stats", params={"floor": 1}).json()["total_votes"] == 1
    assert client.get("/api/v1/stats", params={"floor": 9}).json()["stands"] == []
    assert client.get("/api/v1/stats", params={"floor": "abc"}).status_code == 422


def test_generated_at_is_utc_iso():
    ts = client.get("/api/v1/stats").json()["generated_at"]
    assert ts.endswith("Z")
    assert datetime.fromisoformat(ts.replace("Z", "+00:00")).utcoffset().total_seconds() == 0


def test_single_stand_stats():
    vote("S201", "anna.a", 5, True)
    d = client.get("/api/v1/stands/S201/stats").json()
    assert d["votes"] == 1 and d["rating_sum"] == 5 and d["favorites"] == 1
    assert client.get("/api/v1/stands/XXX/stats").status_code == 404
