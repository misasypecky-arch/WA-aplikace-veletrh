import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
URL = "/api/v1/stands/S201/votes"


def test_vote_saved():
    r = client.post(URL, json={"username": "novak.jan", "rating": 5, "favorite": True})
    assert r.status_code == 201
    assert r.json()["stand_id"] == "S201" and r.json()["rating"] == 5


def test_second_vote_same_user_is_409_case_insensitive():
    assert client.post(URL, json={"username": "novak.jan", "rating": 5, "favorite": True}).status_code == 201
    r = client.post(URL, json={"username": "Novák.Jan".replace("á", "a"), "rating": 1, "favorite": False})
    assert r.status_code == 409


def test_same_user_can_vote_for_another_stand():
    assert client.post(URL, json={"username": "novak.jan", "rating": 5}).status_code == 201
    assert client.post("/api/v1/stands/S202/votes", json={"username": "novak.jan", "rating": 4}).status_code == 201


def test_diacritics_username_ok_and_case_folded():
    assert client.post(URL, json={"username": "Žofie.Nováková", "rating": 3}).status_code == 201
    assert client.post(URL, json={"username": "žofie.nováková", "rating": 3}).status_code == 409


def test_bad_json_from_assignment_is_422():
    r = client.post(URL, content=json.dumps({"username": "x", "rating": 9}),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    fields = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"username", "rating"} <= fields


def test_invalid_values_are_422():
    for body in (
        {"username": "ab", "rating": 3},                     # krátké jméno
        {"username": "novak jan", "rating": 3},              # mezera
        {"username": "novak.jan", "rating": 0},
        {"username": "novak.jan", "rating": 6},
        {"username": "novak.jan", "rating": "5"},            # řetězec místo čísla
        {"username": "novak.jan", "rating": True},           # bool není číslo
        {"username": "novak.jan", "rating": 5, "favorite": "yes"},
        {"username": "novak.jan", "rating": 5, "extra": 1},
        {"rating": 5},
    ):
        assert client.post(URL, json=body).status_code == 422, body


def test_unknown_stand_is_404():
    assert client.post("/api/v1/stands/XXX/votes", json={"username": "novak.jan", "rating": 5}).status_code == 404


def test_docs_describe_all_codes_and_schema():
    op = client.get("/openapi.json").json()["paths"]["/api/v1/stands/{stand_id}/votes"]["post"]
    assert {"201", "404", "409", "422"} <= set(op["responses"])
    assert "requestBody" in op


def test_survey_page():
    r = client.get("/s/S201")
    assert r.status_code == 200 and "Rezervační systém" in r.text
    assert client.get("/s/XXX").status_code == 404
