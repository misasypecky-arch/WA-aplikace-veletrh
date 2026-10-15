# Terminál (server B)

    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

Dokumentace: http://localhost:8081/docs · http://localhost:8081/openapi.json

Povolené porty ve školní síti: 8080-8090 a 65525-65535.

Stav: kostra projektu, logika zatím není hotová.
