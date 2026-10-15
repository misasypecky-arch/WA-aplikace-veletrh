# Centrála (server A)

    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8080
    pytest

Dokumentace: http://localhost:8080/docs · http://localhost:8080/openapi.json

## Konfigurace

Zkopíruj `.env.example` na `.env` a nastav `PUBLIC_URL` na adresu, kterou uvidí telefon
(např. `http://10.2.0.12:8080`). Škola povoluje porty 8080–8090 a 65525–65535.
Server pro telefony spusť s `--host 0.0.0.0`.

QR kódy: `/qr` (stránka k tisku), `/qr/{stand_id}.svg` (jeden kód).
