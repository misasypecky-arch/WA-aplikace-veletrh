"""Stránka dotazníku, kterou telefon otevře po naskenování QR kódu (/s/{stand})."""

import json
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .data import find_stand

router = APIRouter(tags=["survey"])

PAGE = """<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hodnocení: __TITLE__</title>
<style>
  :root { --bg:#f2f5fb; --card:#fff; --ink:#15203b; --muted:#5a6580; --line:#d3daea; --accent:#3b44d1;
          --fav:#e8a317; --ok:#17794a; --err:#b3261e; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#10152a; --card:#1a2140; --ink:#eef1fb; --muted:#9aa5c6; --line:#2d3760; --accent:#8e96ff;
            --fav:#ffc247; --ok:#5fd39b; --err:#ff8f86; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:17px/1.45 system-ui, "Segoe UI", sans-serif; }
  main { max-width: 34rem; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
  h1 { font-size: 1.5rem; line-height: 1.2; margin: .2rem 0 .4rem; }
  .meta { color: var(--muted); margin: 0 0 1.4rem; }
  form, .result { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1.1rem; }
  label.field, legend { display:block; font-weight:600; margin-bottom:.35rem; }
  input[type=text] { width:100%; font:inherit; padding:.7rem .8rem; color:var(--ink); background:var(--bg);
                     border:1px solid var(--line); border-radius:8px; }
  input[type=text]:focus-visible, button:focus-visible, .stars input:focus-visible + span { outline:3px solid var(--accent); outline-offset:2px; }
  .hint { color:var(--muted); font-size:.88rem; margin:.3rem 0 1.1rem; }
  fieldset { border:0; padding:0; margin:0 0 1.1rem; }
  .stars { display:flex; gap:.4rem; }
  .stars label { flex:1; }
  .stars input { position:absolute; opacity:0; }
  .stars span { display:block; text-align:center; padding:.65rem 0; border:1px solid var(--line); border-radius:8px;
                background:var(--bg); font-weight:600; cursor:pointer; }
  .stars input:checked + span { background:var(--accent); border-color:var(--accent); color:var(--card); }
  .fav { display:flex; gap:.6rem; align-items:center; margin-bottom:1.3rem; }
  .fav input { width:1.4rem; height:1.4rem; accent-color: var(--fav); }
  button { width:100%; font:inherit; font-weight:700; padding:.85rem; border:0; border-radius:10px;
           background:var(--accent); color:var(--card); cursor:pointer; }
  button:disabled { opacity:.6; }
  .result { margin-top:1rem; }
  .result.ok { border-color:var(--ok); } .result.err { border-color:var(--err); }
  .result strong { display:block; margin-bottom:.2rem; }
  .result.ok strong { color:var(--ok); } .result.err strong { color:var(--err); }
  [hidden] { display:none !important; }
</style>
</head>
<body>
<main>
  <h1>__TITLE__</h1>
  <p class="meta">__AUTHORS__ · třída __CLASS__ · učebna __ROOM__</p>

  <form id="form" novalidate>
    <label class="field" for="username">Uživatelské jméno</label>
    <input id="username" name="username" type="text" autocomplete="username" autocapitalize="none"
           spellcheck="false" required minlength="3" maxlength="32" placeholder="novak.jan">
    <p class="hint">3–32 znaků: písmena, číslice, tečka, podtržítko nebo pomlčka.</p>

    <fieldset>
      <legend>Hodnocení (1 nejhorší, 5 nejlepší)</legend>
      <div class="stars">
        <label><input type="radio" name="rating" value="1"><span>1</span></label>
        <label><input type="radio" name="rating" value="2"><span>2</span></label>
        <label><input type="radio" name="rating" value="3"><span>3</span></label>
        <label><input type="radio" name="rating" value="4"><span>4</span></label>
        <label><input type="radio" name="rating" value="5"><span>5</span></label>
      </div>
    </fieldset>

    <label class="fav"><input id="favorite" type="checkbox"> Je to můj favorit</label>
    <button id="send" type="submit">Odeslat hlas</button>
  </form>

  <div id="result" class="result" role="status" aria-live="polite" hidden></div>
</main>
<script>
  const STAND_ID = __STAND_ID_JSON__;
  const form = document.getElementById("form");
  const box = document.getElementById("result");
  const send = document.getElementById("send");

  function show(kind, title, text) {
    box.className = "result " + kind;
    box.replaceChildren();
    const s = document.createElement("strong"); s.textContent = title;
    const p = document.createElement("span"); p.textContent = text;
    box.append(s, p);
    box.hidden = false;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rating = form.querySelector("input[name=rating]:checked");
    const body = {
      username: document.getElementById("username").value.trim(),
      rating: rating ? Number(rating.value) : null,
      favorite: document.getElementById("favorite").checked,
    };
    send.disabled = true;
    try {
      const r = await fetch("/api/v1/stands/" + encodeURIComponent(STAND_ID) + "/votes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.status === 201) {
        form.hidden = true;
        show("ok", "Hlas uložen", "Děkujeme za hodnocení.");
      } else if (r.status === 409) {
        form.hidden = true;
        show("err", "Už jste hlasoval(a)", "Pro tento stánek lze hlasovat jen jednou.");
      } else if (r.status === 422) {
        const d = await r.json();
        const fields = (d.detail || []).map(x => (x.loc || []).slice(-1)[0]).filter(Boolean);
        const names = { username: "uživatelské jméno", rating: "hodnocení", favorite: "favorit" };
        const list = [...new Set(fields)].map(f => names[f] || f).join(", ");
        show("err", "Zkontrolujte údaje", list ? "Neplatné: " + list + "." : "Údaje nejsou platné.");
      } else if (r.status === 404) {
        show("err", "Stánek neexistuje", "Naskenujte QR kód znovu.");
      } else {
        show("err", "Něco se nepovedlo", "Zkuste to prosím za chvíli (chyba " + r.status + ").");
      }
    } catch (err) {
      show("err", "Centrála neodpovídá", "Zkontrolujte připojení a zkuste to znovu.");
    } finally {
      send.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@router.get(
    "/s/{stand_id}",
    response_class=HTMLResponse,
    summary="Dotazník stánku (stránka pro mobil)",
    responses={404: {"description": "Stánek neexistuje.", "content": {"text/html": {}}}},
)
def survey_page(stand_id: str) -> HTMLResponse:
    stand = find_stand(stand_id)
    if stand is None:
        return HTMLResponse("<!doctype html><meta charset=utf-8><title>Stánek neexistuje</title>"
                            "<p style='font:18px system-ui;padding:2rem'>Stánek neexistuje. Naskenujte QR kód znovu.</p>",
                            status_code=404)
    html = (
        PAGE.replace("__TITLE__", escape(stand.title))
        .replace("__AUTHORS__", escape(", ".join(stand.authors)))
        .replace("__CLASS__", escape(stand.class_name))
        .replace("__ROOM__", escape(stand.room))
        # </ se escapuje, aby se id nikdy nedalo zavřít <script> blok
        .replace("__STAND_ID_JSON__", json.dumps(stand.id).replace("</", "<\\/"))
    )
    return HTMLResponse(html)
