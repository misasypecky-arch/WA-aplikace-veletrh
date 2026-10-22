"""Aktuální statistika patra + paměť už zpracovaných X-Event-Id (idempotence)."""

import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone

MAX_SEEN = 10_000  # kolik posledních id událostí si pamatujeme


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class Vote:
    stand_id: str
    title: str | None
    rating: int
    favorite: bool
    created_at: datetime | None = None


class StatsStore:
    def __init__(self, floor: int) -> None:
        self.floor = floor
        self._lock = threading.Lock()
        self._stands: dict[str, dict] = {}
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._buffer: list[Vote] = []
        self._loaded = False

    # -------------------------------------------------------------- snapshot (#10)

    @property
    def loaded(self) -> bool:
        return self._loaded

    def apply_snapshot(self, snapshot: dict) -> None:
        """Nahradí stav snapshotem z centrály. Události, které přišly dřív, než snapshot dorazil (byly
        zbufferované), se přičtou jen tehdy, když vznikly PO okamžiku snapshotu – jinak v něm už jsou."""
        stands: dict[str, dict] = {}
        for s in snapshot.get("stands", []):
            if s.get("floor") is not None and int(s["floor"]) != self.floor:
                continue
            votes = int(s.get("votes", 0))
            if "rating_sum" in s:
                rating_sum = int(s["rating_sum"])
            else:  # centrála bez rating_sum: dopočítáme z průměru
                rating_sum = round(float(s.get("avg_rating") or 0) * votes)
            stands[str(s["stand_id"])] = {
                "stand_id": str(s["stand_id"]),
                "title": s.get("title") or str(s["stand_id"]),
                "votes": votes,
                "rating_sum": rating_sum,
                "favorites": int(s.get("favorites", 0)),
            }
        generated_at = parse_iso(snapshot.get("generated_at"))
        with self._lock:
            self._stands = stands
            self._loaded = True
            buffered, self._buffer = self._buffer, []
            for vote in buffered:
                if vote.created_at is None or generated_at is None or vote.created_at > generated_at:
                    self._add(vote)

    # ------------------------------------------------------------ webhooky (#07, #09)

    def handle_event(self, event_id: str, vote: Vote) -> str:
        """Zpracuje událost přesně jednou. Vrací 'applied', 'buffered' (ještě nemáme snapshot) nebo 'duplicate'."""
        with self._lock:
            if event_id in self._seen:
                return "duplicate"
            self._seen[event_id] = None
            while len(self._seen) > MAX_SEEN:
                self._seen.popitem(last=False)  # zapomeneme nejstarší id
            if not self._loaded:
                self._buffer.append(vote)
                return "buffered"
            self._add(vote)
            return "applied"

    def _add(self, vote: Vote) -> None:
        row = self._stands.setdefault(
            vote.stand_id,
            {"stand_id": vote.stand_id, "title": vote.title or vote.stand_id, "votes": 0, "rating_sum": 0, "favorites": 0},
        )
        row["votes"] += 1
        row["rating_sum"] += vote.rating
        row["favorites"] += 1 if vote.favorite else 0

    # ------------------------------------------------------------------ zobrazení

    def view(self) -> dict:
        with self._lock:
            rows = [
                {
                    "stand_id": r["stand_id"],
                    "title": r["title"],
                    "votes": r["votes"],
                    "avg_rating": round(r["rating_sum"] / r["votes"], 2) if r["votes"] else 0.0,
                    "favorites": r["favorites"],
                }
                for r in self._stands.values()
            ]
        rows.sort(key=lambda r: (-r["avg_rating"], -r["votes"], r["title"]))
        return {"floor": self.floor, "total_votes": sum(r["votes"] for r in rows), "stands": rows}

    def reset(self) -> None:
        with self._lock:
            self._stands.clear()
            self._seen.clear()
            self._buffer.clear()
            self._loaded = False
