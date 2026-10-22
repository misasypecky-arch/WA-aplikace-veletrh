# Terminál (server B)

    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8081
    pytest

Obrazovka: http://localhost:8081/ · dokumentace: http://localhost:8081/docs · http://localhost:8081/openapi.json
Povolené porty ve školní síti: 8080–8090 a 65525–65535.

## Konfigurace (`.env`)

| proměnná | význam |
|---|---|
| `CENTRAL_URL` | adresa centrály (bez `/api/v1`) |
| `MY_URL` | veřejná adresa tohoto terminálu; callback je `{MY_URL}/webhooks/votes` (jde přepsat `CALLBACK_URL`) |
| `FLOOR` | patro obrazovky |
| `POLL_INTERVAL` | `>0` zapne polling (#05, jen na ukázku); výchozí `0` |

Dva terminály najednou = dva `.env` / dvě proměnné prostředí a jiný `--port`, např.
`FLOOR=3 MY_URL=http://localhost:8082 uvicorn app.main:app --port 8082`.

## Jak to funguje

1. Start: `POST /api/v1/subscriptions` (id + secret), potom `GET /api/v1/stats?floor=N` (snapshot). Pořadí je důležité.
   Když centrála neběží, terminál startuje dál a zkouší to opakovaně.
2. `POST /webhooks/votes`: podpis (HMAC nad surovými bajty) → 401 při chybě; teprve pak se parsuje JSON.
   Duplicitní `X-Event-Id` = `200` beze změny (pamatuje se posledních 10 000 id).
3. Hlasy z webhooků, které dorazí před snapshotem, se zbufferují a po snapshotu se přičtou jen ty,
   které vznikly po jeho `generated_at` (jinak by se započítaly dvakrát).
4. Vypnutí: `DELETE` odběru. Po restartu začíná od nuly a znovu stáhne snapshot.
5. `GET /stats` – co terminál zobrazuje (seřazeno podle průměru), `GET /status` – stav připojení,
   `GET /` – obrazovka (`app/static/index.html`), obnovuje se každé 2 s z vlastního `/stats`.
