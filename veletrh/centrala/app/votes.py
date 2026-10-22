from fastapi import APIRouter, BackgroundTasks, HTTPException

from .data import find_stand
from .models import VoteIn, VoteOut
from .store import votes
from .webhooks import dispatch_vote

router = APIRouter(tags=["votes"])


@router.post(
    "/stands/{stand_id}/votes",
    response_model=VoteOut,
    status_code=201,
    summary="Odeslat hlas pro stánek",
    responses={
        201: {"description": "Hlas uložen."},
        404: {"description": "Stánek neexistuje."},
        409: {"description": "Tento uživatel už pro stánek hlasoval (jméno se porovnává bez ohledu na velikost písmen)."},
        422: {"description": "Neplatné tělo: odpověď říká, které pole a proč je špatně."},
    },
)
def create_vote(stand_id: str, vote: VoteIn, background: BackgroundTasks) -> VoteOut:
    stand = find_stand(stand_id)
    if stand is None:
        raise HTTPException(status_code=404, detail="Stánek neexistuje.")
    record = votes.add(stand_id, vote)
    if record is None:
        raise HTTPException(status_code=409, detail="Pro tento stánek jste už hlasoval(a).")
    # Rozeslání terminálům proběhne až po odeslání odpovědi žákovi.
    background.add_task(dispatch_vote, record, stand)
    return record
