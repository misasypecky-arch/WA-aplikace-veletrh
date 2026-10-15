import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.qr import survey_url

client = TestClient(app)


def test_svg_ok():
    r = client.get("/qr/S201.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text


def test_svg_unknown_stand():
    assert client.get("/qr/XXX.svg").status_code == 404


def test_url_from_env(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "http://10.2.0.12:8080/")
    assert survey_url("S201") == "http://10.2.0.12:8080/s/S201"


def test_qr_encodes_configured_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "http://10.2.0.12:8080")
    a = client.get("/qr/S201.svg").text
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8080")
    b = client.get("/qr/S201.svg").text
    assert a != b  # jiná adresa = jiný QR kód


def test_sheet_lists_all_stands():
    from app.data import STANDS
    r = client.get("/qr")
    assert r.status_code == 200
    for s in STANDS:
        assert f"/qr/{s.id}.svg" in r.text
        assert s.title in r.text


def test_openapi_has_qr():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/qr/{stand_id}.svg" in paths and "/qr" in paths
