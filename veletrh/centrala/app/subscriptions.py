from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response

from .models import SubscriptionCreated, SubscriptionIn, SubscriptionOut, VoteEvent
from .store import Subscription, subscriptions

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Popis webhooku pro /docs (OpenAPI "callbacks"): co a v jakém tvaru centrála posílá na callback_url.
callback_router = APIRouter()


@callback_router.post(
    "{$request.body#/callback_url}",
    summary="Událost vote.created (webhook)",
    description=(
        "Po uložení každého hlasu centrála zavolá `POST` na `callback_url` všech odběrů, jejichž `floor` "
        "je patro stánku, nebo `null`.\n\n"
        "**Hlavičky**\n"
        "- `X-Event-Id` – id události; při opakovaném doručení stejné. Terminál si id pamatuje a duplicitu ignoruje.\n"
        "- `X-Signature` – `sha256=<hex>`, kde hex je HMAC-SHA256 **surových bajtů těla** s klíčem `secret` "
        "z odpovědi na přihlášení.\n\n"
        "**Doručení** je úspěšné jen při odpovědi `2xx` do 3 s. Jinak centrála opakuje po 1 s, 2 s a 4 s "
        "(stejné tělo i podpis) a pak to vzdá. Duplicitní událost proto terminál potvrzuje `200`, ne `409`."
    ),
    responses={
        200: {"description": "Událost přijata (i když už byla zpracována dříve)."},
        401: {"description": "Chybějící nebo neplatný podpis."},
    },
)
def vote_created_callback(
    event: VoteEvent,
    x_event_id: Annotated[str, Header(description="Id události.")],
    x_signature: Annotated[str, Header(description="`sha256=<hex HMAC-SHA256 těla>`.")],
):
    """Jen pro dokumentaci, nikdy se nevolá."""


def _out(sub: Subscription) -> SubscriptionOut:
    return SubscriptionOut(id=sub.id, callback_url=sub.callback_url, floor=sub.floor, created_at=sub.created_at)


@router.post(
    "",
    response_model=SubscriptionCreated,
    status_code=201,
    summary="Přihlásit terminál k odběru událostí",
    description=(
        "Terminál při startu pošle svoji adresu a patro. Vrácený `secret` se zobrazí **jen jednou**; "
        "slouží k ověření podpisu webhooků. Nové přihlášení na stejnou `callback_url` nahradí staré.\n\n"
        "Doporučené pořadí v terminálu: nejdřív tento odběr, potom `GET /api/v1/stats?floor=N` (snapshot)."
    ),
    callbacks=callback_router.routes,
)
def create_subscription(body: SubscriptionIn) -> SubscriptionCreated:
    sub = subscriptions.add(body.callback_url, body.floor)
    return SubscriptionCreated(**_out(sub).model_dump(), secret=sub.secret)


@router.get("", response_model=list[SubscriptionOut], summary="Seznam odběrů (bez secret)")
def list_subscriptions() -> list[SubscriptionOut]:
    return [_out(s) for s in subscriptions.all()]


@router.delete(
    "/{subscription_id}",
    status_code=204,
    summary="Zrušit odběr",
    responses={204: {"description": "Odběr zrušen."}, 404: {"description": "Odběr neexistuje."}},
)
def delete_subscription(subscription_id: str) -> Response:
    if not subscriptions.delete(subscription_id):
        raise HTTPException(status_code=404, detail="Odběr neexistuje.")
    return Response(status_code=204)
