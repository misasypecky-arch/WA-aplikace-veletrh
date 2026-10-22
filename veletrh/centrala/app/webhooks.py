"""Rozesílání událostí terminálům (#07), podpisy (#08) a opakování doručení (#09)."""

import asyncio
import hashlib
import hmac
import json
import logging
import uuid

import httpx

from .models import Stand, VoteOut
from .store import Subscription, subscriptions

log = logging.getLogger("uvicorn.error")  # aby se hlášky objevily v logu uvicornu

DELIVERY_TIMEOUT = 3.0  # úspěch = odpověď 2xx do 3 s
RETRY_DELAYS = (1.0, 2.0, 4.0)  # pauzy před 2., 3. a 4. pokusem


def sign(secret: str, body: bytes) -> str:
    """Hodnota hlavičky X-Signature: sha256=<hex HMAC-SHA256 surových bajtů těla>."""
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def build_event(vote: VoteOut, stand: Stand) -> tuple[str, bytes]:
    """Tělo události se serializuje JEDNOU. Podepisují se a odesílají přesně tytéž bajty (i při opakování)."""
    event_id = "evt_" + uuid.uuid4().hex
    event = {
        "id": event_id,
        "type": "vote.created",
        "created_at": vote.created_at,
        "data": {
            "stand_id": stand.id,
            "title": stand.title,
            "floor": stand.floor,
            "username": vote.username,
            "rating": vote.rating,
            "favorite": vote.favorite,
        },
    }
    return event_id, json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=DELIVERY_TIMEOUT)


async def _deliver(client: httpx.AsyncClient, sub: Subscription, event_id: str, body: bytes) -> bool:
    headers = {
        "Content-Type": "application/json",
        "X-Event-Id": event_id,
        "X-Signature": sign(sub.secret, body),  # stejné tělo => stejný podpis při každém opakování
    }
    attempts = len(RETRY_DELAYS) + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = await asyncio.wait_for(
                client.post(sub.callback_url, content=body, headers=headers), timeout=DELIVERY_TIMEOUT
            )
            if 200 <= resp.status_code < 300:
                return True
            reason = f"odpověď HTTP {resp.status_code}"
        except asyncio.TimeoutError:
            reason = f"timeout ({DELIVERY_TIMEOUT:g} s)"
        except Exception as exc:  # síťová chyba, nedostupný terminál…
            reason = f"{type(exc).__name__}: {exc}"
        log.warning("Doručení %s na %s: pokus %d/%d selhal (%s)", event_id, sub.callback_url, attempt, attempts, reason)
        if attempt < attempts:
            await asyncio.sleep(RETRY_DELAYS[attempt - 1])
    log.error("Doručení události %s na %s se definitivně nezdařilo.", event_id, sub.callback_url)
    return False


async def dispatch_vote(vote: VoteOut, stand: Stand) -> None:
    """Pošle událost všem odběrům pro patro stánku. Běží na pozadí až po odeslání odpovědi žákovi
    a nikdy nevyhodí výjimku – nedostupný terminál nesmí ohrozit uložení hlasu."""
    try:
        targets = subscriptions.for_floor(stand.floor)
        if not targets:
            return
        event_id, body = build_event(vote, stand)

        async def one(sub: Subscription) -> None:
            ok = await _deliver(client, sub, event_id, body)
            if subscriptions.report(sub.id, ok):
                log.warning("Odběr %s (%s) zrušen: terminál opakovaně neodpovídá.", sub.id, sub.callback_url)

        async with make_client() as client:
            await asyncio.gather(*(one(s) for s in targets))
    except Exception:
        log.exception("Rozeslání události selhalo")
