from fastapi import FastAPI

app = FastAPI(
    title="Veletrh – terminál (server B)",
    version="0.1.0",
    description="Přijímá webhooky z centrály a zobrazuje statistiku patra.",
)

# TODO: POST /webhooks/votes  (ověření podpisu, deduplikace)
# TODO: GET  /stats           (aktuální statistika patra)
# TODO: startup: POST /subscriptions + GET /stats?floor=N; shutdown: DELETE odběru
