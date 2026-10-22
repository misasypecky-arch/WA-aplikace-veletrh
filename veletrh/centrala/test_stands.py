from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_all():
    r = client.get("/api/v1/stands")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 8
    assert {s["floor"] for s in data} >= {1, 2}


def test_stand_shape():
    s = client.get("/api/v1/stands").json()[0]
    assert set(s) == {"id", "title", "authors", "class_name", "floor", "room"}


def test_filter_floor():
    r = client.get("/api/v1/stands", params={"floor": 2})
    assert r.status_code == 200
    assert r.json() and all(s["floor"] == 2 for s in r.json())


def test_filter_empty_floor():
    assert client.get("/api/v1/stands", params={"floor": 9}).json() == []


def test_filter_invalid():
    assert client.get("/api/v1/stands", params={"floor": "abc"}).status_code == 422


def test_detail():
    assert client.get("/api/v1/stands/S201").json()["room"] == "201"
    assert client.get("/api/v1/stands/XXX").status_code == 404


def test_openapi_and_docs():
    spec = client.get("/openapi.json").json()
    assert "/api/v1/stands" in spec["paths"]
    assert client.get("/docs").status_code == 200
