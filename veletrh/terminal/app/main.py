import asyncio
import contextlib
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import ValidationError

from . import config, signature
from .central_client import CentralClient
from .models import Status, TerminalStats, WebhookEvent
from .store import StatsStore, Vote, parse_iso

log = logging.getLogger("uvicorn.error")
STATIC = Path(__file__).parent / "static"


@dataclass
class Session:
    subscription_id: str | None = None
    secret: str | None = None


session = Session()
store = StatsStore(floor=config.floor())


# ----------------------------------------------------- napojení na centrálu (#06, #10)


async def connect_loop(central: CentralClient) -> None:
    """Pořadí je důležité: nejdřív odběr, potom snapshot. Hlas, který přijde mezi tím, se zbufferuje
    a po načtení snapshotu se doplní (viz StatsStore.apply_snapshot)."""
    while True:
        try:
            if session.subscription_id is None:
                sub_id, secret = await central.subscribe(config.callback_url(), store.floor)
                session.subscription_id, session.secret = sub_id, secret
                log.info("Přihlášen k odběru %s (patro %s)", sub_id, store.floor)
            store.apply_snapshot(await central.snapshot(store.floor))
            log.info("Snapshot načten, terminál běží (patro %s)", store.floor)
            return
        except Exception as exc:
            log.warning("Centrála %s není dostupná (%s: %s), zkouším znovu za %g s",
                        config.central_url(), type(exc).__name__, exc, config.retry_delay())
            await asyncio.sleep(config.retry_delay())


async def poll_loop(central: CentralClient, interval: float) -> None:
    """Jen pro ukázku #05: dokola se ptá centrály. S odběrem a webhooky se nepoužívá."""
    log.warning("Běží POLLING každých %g s. Pro ostrý provoz nastav POLL_INTERVAL=0.", interval)
    while True:
        try:
            store.apply_snapshot(await central.snapshot(store.floor))
        except Exception as exc:
            log.warning("Polling selhal (%s: %s)", type(exc).__name__, exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    central = CentralClient(config.central_url())
    interval = config.poll_interval()
    task = asyncio.create_task(poll_loop(central, interval) if interval > 0 else connect_loop(central))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        if session.subscription_id:  # korektní odhlášení; při pádu to centrála pozná podle neúspěšných doručení
            try:
                await central.unsubscribe(session.subscription_id)
                log.info("Odběr %s zrušen", session.subscription_id)
            except Exception as exc:
                log.warning("Odběr se nepodařilo zrušit (%s: %s)", type(exc).__name__, exc)
        await central.aclose()


app = FastAPI(
    title="Veletrh – terminál (server B)",
    version="0.1.0",
    description="Přijímá webhooky z centrály a zobrazuje statistiku patra.",
    lifespan=lifespan,
)


# ----------------------------------------------------------------- webhook (#07–#09)


async def verified_body(request: Request, x_signature: Annotated[str | None, Header(
        description="`sha256=<hex HMAC-SHA256 surových bajtů těla>` s klíčem `secret` z přihlášení.")] = None) -> bytes:
    """Ověří podpis nad SUROVÝMI bajty těla ještě před parsováním JSON. Při neplatném podpisu skončí 401
    a nic se nezapočítá. (Totéž by šlo udělat jako middleware; závislost je jen přehlednější v /docs.)"""
    if session.secret is None:
        raise HTTPException(status_code=503, detail="Terminál ještě není přihlášen k centrále.")
    body = await request.body()
    if not signature.verify(session.secret, body, x_signature):
        raise HTTPException(status_code=401, detail="Chybějící nebo neplatný podpis.")
    return body


EXAMPLE_EVENT = {
    "id": "evt_5c1e0b7a",
    "type": "vote.created",
    "created_at": "2026-10-22T08:15:00.123456Z",
    "data": {"stand_id": "S201", "title": "Rezervační systém pro školní učebny", "floor": 2,
             "username": "novak.jan", "rating": 5, "favorite": True},
}


@app.post(
    "/webhooks/votes",
    tags=["webhooks"],
    summary="Příjem události vote.created z centrály",
    description="Ověří `X-Signature`, zahodí duplicitu podle `X-Event-Id` (stále `200`) a přičte hlas do statistiky.",
    responses={
        200: {"description": "Událost přijata (nebo už dříve zpracována)."},
        401: {"description": "Chybějící nebo neplatný podpis, nic se nezapočítalo."},
        422: {"description": "Podpis sedí, ale tělo nemá očekávaný tvar."},
        503: {"description": "Terminál se ještě nepřihlásil k centrále (nemá secret)."},
    },
    openapi_extra={"requestBody": {"required": True, "content": {"application/json": {
        "schema": {"type": "object"}, "example": EXAMPLE_EVENT}}}},
)
async def receive_vote(
    body: Annotated[bytes, Depends(verified_body)],
    x_event_id: Annotated[str | None, Header(description="Id události; stejné při opakovaném doručení.")] = None,
) -> dict:
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=422, detail="Tělo není platný JSON.")
    try:
        event = WebhookEvent.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json(include_url=False)))

    if event.type != "vote.created":
        return {"status": "ignored"}
    if event.data.floor is not None and event.data.floor != store.floor:
        return {"status": "ignored"}  # hlas z jiného patra se nezapočítá

    event_id = x_event_id or event.id
    if not event_id:
        raise HTTPException(status_code=422, detail="Chybí X-Event-Id.")

    vote = Vote(
        stand_id=event.data.stand_id,
        title=event.data.title,
        rating=event.data.rating,
        favorite=event.data.favorite,
        created_at=parse_iso(event.created_at),
    )
    # Duplicitní událost = 200 beze změny. Kdybychom vrátili 409, centrála by ji považovala za nedoručenou
    # a posílala by ji znovu.
    return {"status": store.handle_event(event_id, vote)}


# ------------------------------------------------------------------ obrazovka (#05)


@app.get("/stats", response_model=TerminalStats, tags=["stats"], summary="Statistika patra, seřazená podle průměru")
def get_stats() -> dict:
    return store.view()


@app.get("/status", response_model=Status, tags=["stats"], summary="Stav připojení k centrále")
def get_status() -> dict:
    return {
        "floor": store.floor,
        "loaded": store.loaded,
        "subscribed": session.subscription_id is not None,
        "mode": "polling" if config.poll_interval() > 0 else "webhooks",
    }


@app.get("/", include_in_schema=False)
def screen() -> FileResponse:
    return FileResponse(STATIC / "index.html")
