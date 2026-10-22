from fastapi import APIRouter, HTTPException, Query

from .data import find_stand
from .models import StandStats, Stats
from .store import votes

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=Stats, summary="Statistika stánků (volitelně jen jednoho patra)")
def get_stats(
    floor: int | None = Query(default=None, ge=0, description="Jen stánky z tohoto patra. Bez parametru všechny."),
) -> Stats:
    return votes.stats(floor)


@router.get(
    "/stands/{stand_id}/stats",
    response_model=StandStats,
    summary="Statistika jednoho stánku",
    responses={404: {"description": "Stánek neexistuje."}},
)
def get_stand_stats(stand_id: str) -> StandStats:
    stand = find_stand(stand_id)
    if stand is None:
        raise HTTPException(status_code=404, detail="Stánek neexistuje.")
    return votes.stand_stats(stand)
