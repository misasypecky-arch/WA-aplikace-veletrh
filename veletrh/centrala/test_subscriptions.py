import re

from fastapi.testclient import TestClient

from app.main import app
from app.store import subscriptions

client = TestClient(app)
URL = "/api/v1/subscriptions"


def test_create_returns_id_and_secret_once():
    r = client.post(URL, json={"callback_url": "http://localhost:8081/webhooks/votes", "floor": 2})
    assert r.status_code == 201
    d = r.json()
    assert d["id"] and re.fullmatch(r"[0-9a-f]{64}", d["secret"])  # 32 bajtů = 64 hex znaků
    listed = client.get(URL).json()
    assert len(listed) == 1 and "secret" not in listed[0] and listed[0]["floor"] == 2


def test_two_terminals_both_listed_and_secrets_differ():
    a = client.post(URL, json={"callback_url": "http://localhost:8081/webhooks/votes", "floor": 2}).json()
    b = client.post(URL, json={"callback_url": "http://localhost:8082/webhooks/votes", "floor": 3}).json()
    assert a["secret"] != b["secret"]
    assert len(client.get(URL).json()) == 2


def test_same_callback_replaces_old_subscription():
    first = client.post(URL, json={"callback_url": "http://localhost:8081/webhooks/votes", "floor": 2}).json()
    second = client.post(URL, json={"callback_url": "http://localhost:8081/webhooks/votes", "floor": 3}).json()
    listed = client.get(URL).json()
    assert [s["id"] for s in listed] == [second["id"]] and listed[0]["floor"] == 3
    assert client.delete(f"{URL}/{first['id']}").status_code == 404


def test_floor_null_is_allowed():
    assert client.post(URL, json={"callback_url": "http://localhost:8081/x"}).json()["floor"] is None


def test_invalid_body_is_422():
    for body in ({}, {"callback_url": "not a url"}, {"callback_url": "ftp://x/y"},
                 {"callback_url": "http://x/y", "floor": -1}, {"callback_url": "http://x/y", "floor": "a"}):
        assert client.post(URL, json=body).status_code == 422, body


def test_delete():
    sid = client.post(URL, json={"callback_url": "http://localhost:8081/x", "floor": 2}).json()["id"]
    assert client.delete(f"{URL}/{sid}").status_code == 204
    assert client.delete(f"{URL}/{sid}").status_code == 404
    assert client.get(URL).json() == []


def test_docs_describe_callback():
    op = client.get("/openapi.json").json()["paths"][URL]["post"]
    assert "callbacks" in op
