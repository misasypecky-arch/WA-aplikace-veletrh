# Centrála (server A)

    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
    pytest

Dokumentace: http://localhost:8080/docs · http://localhost:8080/openapi.json
Povolené porty ve školní síti: 8080–8090 a 65525–65535.

## Konfigurace (`.env`)

| proměnná | význam |
|---|---|
| `PUBLIC_URL` | adresa, kterou uvidí telefon (např. `http://10.2.0.12:8080`); je v QR kódech |
| `MAX_DELIVERY_FAILURES` | po kolika po sobě nedoručených událostech se odběr zruší (výchozí 5, `0` = nikdy) |

## Endpointy

| | |
|---|---|
| `GET /api/v1/stands`, `/api/v1/stands/{id}` | #01 katalog (filtr `?floor=N`) |
| `GET /qr`, `/qr/{id}.svg` | #02 QR kódy |
| `GET /s/{id}` | #03 stránka dotazníku pro mobil |
| `POST /api/v1/stands/{id}/votes` | #03 hlas: 201 / 404 / 409 / 422 |
| `GET /api/v1/stats?floor=N`, `/api/v1/stands/{id}/stats` | #04 statistika |
| `POST/GET /api/v1/subscriptions`, `DELETE …/{id}` | #06 odběry |
| webhook `POST {callback_url}` | #07–#09 událost `vote.created` (popsaná v `/docs` u `POST /subscriptions` jako callback) |

## Webhook `vote.created`

    POST {callback_url}
    X-Event-Id: evt_<hex>
    X-Signature: sha256=<hex HMAC-SHA256 surových bajtů těla s klíčem secret>

    {"id":"evt_…","type":"vote.created","created_at":"2026-10-22T08:15:00.123456Z",
     "data":{"stand_id":"S201","title":"…","floor":2,"username":"novak.jan","rating":5,"favorite":true}}

- Tělo se serializuje jednou a podepisují se přesně tytéž bajty. Opakování posílá stejné tělo i podpis.
- Doručení = odpověď 2xx do 3 s, jinak další pokusy po 1 s, 2 s a 4 s. Pak se zaloguje chyba s id události.
- Rozesílání běží na pozadí po odeslání odpovědi žákovi, nedostupný terminál hlas neohrozí.
- Nové přihlášení se stejnou `callback_url` nahradí starý odběr (terminál po restartu).

## Jak centrála pozná, že terminál zmizel?

1. Korektní vypnutí: terminál pošle `DELETE /subscriptions/{id}`.
2. Pád nebo vypnutá síť: DELETE nepřijde. Centrála počítá nedoručené události za sebou
   a po `MAX_DELIVERY_FAILURES` odběr zruší. Úspěšné doručení počítadlo vynuluje.
3. Restart terminálu: nové přihlášení se stejnou adresou starý odběr přepíše.
