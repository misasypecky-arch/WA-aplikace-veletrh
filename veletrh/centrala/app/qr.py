import io
from html import escape

import segno
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import config
from .data import STANDS
from .models import Stand

router = APIRouter(tags=["qr"])


def _find(stand_id: str) -> Stand:
    for s in STANDS:
        if s.id == stand_id:
            return s
    raise HTTPException(status_code=404, detail="Stánek neexistuje.")


def survey_url(stand_id: str) -> str:
    return f"{config.public_url()}/s/{stand_id}"


def _svg(url: str, scale: int = 8) -> str:
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=scale, border=2, xmldecl=False)
    return buf.getvalue().decode("utf-8")


@router.get(
    "/qr/{stand_id}.svg",
    summary="QR kód stánku (SVG)",
    response_class=Response,
    responses={
        200: {"content": {"image/svg+xml": {}}, "description": "QR kód s adresou dotazníku."},
        404: {"description": "Stánek neexistuje."},
    },
)
def qr_svg(stand_id: str) -> Response:
    _find(stand_id)
    return Response(_svg(survey_url(stand_id)), media_type="image/svg+xml")


@router.get(
    "/qr",
    summary="Všechny QR kódy k tisku",
    response_class=HTMLResponse,
)
def qr_sheet() -> HTMLResponse:
    cards = []
    for s in sorted(STANDS, key=lambda s: (s.floor, s.id)):
        cards.append(
            f"""<figure>
  <img src="/qr/{escape(s.id)}.svg" alt="QR kód stánku {escape(s.id)}">
  <figcaption><strong>{escape(s.id)}</strong> · učebna {escape(s.room)}<br>{escape(s.title)}</figcaption>
</figure>"""
        )
    page = f"""<!doctype html>
<html lang="cs"><head><meta charset="utf-8">
<title>QR kódy stánků</title>
<style>
  body {{ font-family: sans-serif; margin: 1.5rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1.5rem; }}
  figure {{ margin: 0; text-align: center; break-inside: avoid; border: 1px solid #ccc; padding: .75rem; }}
  img {{ width: 100%; max-width: 200px; }}
  figcaption {{ font-size: .9rem; }}
  .url {{ color: #555; font-size: .8rem; }}
  @media print {{ .url {{ display: none; }} body {{ margin: 0; }} }}
</style></head><body>
<h1>QR kódy stánků</h1>
<p class="url">Adresa centrály: {escape(config.public_url())}</p>
<div class="grid">
{''.join(cards)}
</div>
</body></html>"""
    return HTMLResponse(page)
