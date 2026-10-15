from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_docs_available():
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


# TODO: platný podpis -> 200, neplatný -> 401, duplicitní X-Event-Id -> 200 bez dvojího započtení
