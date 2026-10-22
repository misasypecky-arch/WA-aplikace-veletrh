from fastapi import APIRouter, FastAPI, HTTPException, Query

from .data import STANDS
from .models import Stand
from .qr import router as qr_router
from .stats import router as stats_router
from .subscriptions import router as subscriptions_router
from .survey import router as survey_router
from .votes import router as votes_router

app = FastAPI(
    title="Veletrh – centrála (server A)",
    version="0.1.0",
    description="Katalog stánků, příjem hlasů, statistika a rozesílání událostí terminálům.",
)

api = APIRouter(prefix="/api/v1")


@api.get("/stands", response_model=list[Stand], tags=["stands"], summary="Seznam stánků")
def list_stands(
    floor: int | None = Query(
        default=None, ge=0, description="Vrátí jen stánky na daném patře. Bez parametru vrátí všechny."
    ),
) -> list[Stand]:
    if floor is None:
        return STANDS
    return [s for s in STANDS if s.floor == floor]


@api.get(
    "/stands/{stand_id}",
    response_model=Stand,
    tags=["stands"],
    summary="Detail stánku",
    responses={404: {"description": "Stánek neexistuje."}},
)
def get_stand(stand_id: str) -> Stand:
    for s in STANDS:
        if s.id == stand_id:
            return s
    raise HTTPException(status_code=404, detail="Stánek neexistuje.")


api.include_router(votes_router)
api.include_router(stats_router)
api.include_router(subscriptions_router)

app.include_router(api)
app.include_router(survey_router)
app.include_router(qr_router)
