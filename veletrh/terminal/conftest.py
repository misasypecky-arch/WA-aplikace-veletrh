import pytest

from app import main

SECRET = "tajny-klic-z-prihlaseni"


@pytest.fixture(autouse=True)
def terminal_state():
    """Terminál pro patro 2, už přihlášený (secret znám), s prázdnou statistikou načtenou ze snapshotu."""
    main.store.floor = 2
    main.store.reset()
    main.session.secret = SECRET
    main.session.subscription_id = "sub_test"
    main.store.apply_snapshot({"generated_at": "2026-10-22T08:00:00.000000Z", "total_votes": 0, "stands": [
        {"stand_id": "S201", "title": "Rezervační systém", "floor": 2, "votes": 0, "rating_sum": 0,
         "avg_rating": 0.0, "favorites": 0},
        {"stand_id": "S202", "title": "Rozvrh na displeji", "floor": 2, "votes": 0, "rating_sum": 0,
         "avg_rating": 0.0, "favorites": 0},
    ]})
    yield
    main.session.secret = None
    main.session.subscription_id = None
