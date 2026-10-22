"""#10: snapshot po startu a slučování s webhooky, které dorazí dřív."""

from app.store import StatsStore, Vote, parse_iso


def snap(votes, generated_at="2026-10-22T08:00:00.000000Z", stand="S201"):
    return {"generated_at": generated_at, "total_votes": votes, "stands": [
        {"stand_id": stand, "title": "Projekt", "floor": 2, "votes": votes, "rating_sum": votes * 4,
         "avg_rating": 4.0 if votes else 0.0, "favorites": 0}]}


def test_snapshot_sets_state_including_rating_sum():
    s = StatsStore(floor=2)
    s.apply_snapshot(snap(2))
    row = s.view()["stands"][0]
    assert row["votes"] == 2 and row["avg_rating"] == 4.0
    s.handle_event("e1", Vote("S201", None, 1, False))  # (8 + 1) / 3
    assert s.view()["stands"][0]["avg_rating"] == 3.0


def test_snapshot_drops_other_floors():
    s = StatsStore(floor=2)
    data = snap(1); data["stands"].append({"stand_id": "S301", "title": "x", "floor": 3, "votes": 5,
                                           "rating_sum": 5, "avg_rating": 1.0, "favorites": 0})
    s.apply_snapshot(data)
    assert [r["stand_id"] for r in s.view()["stands"]] == ["S201"]


def test_snapshot_without_rating_sum_falls_back_to_average():
    s = StatsStore(floor=2)
    s.apply_snapshot({"generated_at": None, "stands": [{"stand_id": "S1", "title": "t", "votes": 2, "avg_rating": 4.5}]})
    assert s.view()["stands"][0]["avg_rating"] == 4.5


def test_events_before_snapshot_are_buffered_and_merged_by_time():
    s = StatsStore(floor=2)
    old = Vote("S201", None, 4, False, parse_iso("2026-10-22T07:59:59.999999Z"))  # už je ve snapshotu
    new = Vote("S201", None, 4, False, parse_iso("2026-10-22T08:00:00.500000Z"))  # vznikl po snapshotu
    assert s.handle_event("e_old", old) == "buffered"
    assert s.handle_event("e_new", new) == "buffered"
    assert s.view()["total_votes"] == 0 and not s.loaded
    s.apply_snapshot(snap(1))  # snapshot už obsahuje 1 hlas (ten starý)
    assert s.view()["total_votes"] == 2  # 1 ze snapshotu + 1 nový, starý se nezapočítal podruhé
    assert s.loaded


def test_duplicate_of_buffered_event_is_ignored():
    s = StatsStore(floor=2)
    v = Vote("S201", None, 5, True, parse_iso("2026-10-22T09:00:00Z"))
    assert s.handle_event("e1", v) == "buffered"
    assert s.handle_event("e1", v) == "duplicate"
    s.apply_snapshot(snap(0))
    assert s.view()["total_votes"] == 1


def test_new_snapshot_replaces_state_for_floor_move():
    s = StatsStore(floor=2)
    s.apply_snapshot(snap(3))
    s.floor = 3
    s.apply_snapshot(snap(1, stand="S301") | {"stands": [{"stand_id": "S301", "title": "Nové patro", "floor": 3,
                                                          "votes": 1, "rating_sum": 5, "favorites": 0}]})
    assert [r["stand_id"] for r in s.view()["stands"]] == ["S301"] and s.view()["floor"] == 3
