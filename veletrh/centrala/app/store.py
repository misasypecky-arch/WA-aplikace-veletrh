"""Úložiště v paměti: hlasy (#03/#04) a odběry terminálů (#06). Po restartu centrály začíná od nuly."""

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .data import STANDS
from .models import Stand, StandStats, Stats, VoteIn, VoteOut


def utc_now_iso() -> str:
    """Aktuální čas v UTC, ISO 8601, s mikrosekundami a příponou Z."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


# ------------------------------------------------------------------- hlasy


def _stand_stats(stand: Stand, votes: list[VoteOut]) -> StandStats:
    total = sum(v.rating for v in votes)
    return StandStats(
        stand_id=stand.id,
        title=stand.title,
        floor=stand.floor,
        votes=len(votes),
        rating_sum=total,
        avg_rating=round(total / len(votes), 2) if votes else 0.0,
        favorites=sum(1 for v in votes if v.favorite),
    )


class VoteStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._votes: list[VoteOut] = []
        self._voted: set[tuple[str, str]] = set()

    def clear(self) -> None:
        with self._lock:
            self._votes.clear()
            self._voted.clear()

    def add(self, stand_id: str, vote: VoteIn) -> VoteOut | None:
        """Uloží hlas. Vrátí None, pokud tento žák už pro stánek hlasoval (jméno bez ohledu na velikost písmen)."""
        key = (stand_id, vote.username.casefold())
        with self._lock:
            if key in self._voted:
                return None
            self._voted.add(key)
            record = VoteOut(
                stand_id=stand_id,
                username=vote.username,
                rating=vote.rating,
                favorite=vote.favorite,
                created_at=utc_now_iso(),
            )
            self._votes.append(record)
            return record

    def _snapshot(self) -> tuple[str, list[VoteOut]]:
        # Čas i kopie hlasů se berou pod stejným zámkem: každý hlas s created_at <= generated_at je ve výpočtu.
        # Terminál na tom staví při slučování snapshotu s webhooky (#10).
        with self._lock:
            return utc_now_iso(), list(self._votes)

    def stats(self, floor: int | None = None) -> Stats:
        generated_at, votes = self._snapshot()
        by_stand: dict[str, list[VoteOut]] = {}
        for v in votes:
            by_stand.setdefault(v.stand_id, []).append(v)
        stands = [
            _stand_stats(s, by_stand.get(s.id, [])) for s in STANDS if floor is None or s.floor == floor
        ]
        return Stats(generated_at=generated_at, total_votes=sum(s.votes for s in stands), stands=stands)

    def stand_stats(self, stand: Stand) -> StandStats:
        _, votes = self._snapshot()
        return _stand_stats(stand, [v for v in votes if v.stand_id == stand.id])


# ------------------------------------------------------------------- odběry


@dataclass
class Subscription:
    id: str
    callback_url: str
    floor: int | None
    secret: str
    created_at: str
    failures: int = 0  # kolik událostí za sebou se nepodařilo doručit


class SubscriptionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, Subscription] = {}

    def clear(self) -> None:
        with self._lock:
            self._subs.clear()

    def add(self, callback_url: str, floor: int | None) -> Subscription:
        """Vytvoří odběr. Nové přihlášení na stejné callback_url nahradí staré (terminál se po restartu
        přihlašuje znovu a starý odběr s neplatným secret by jen zbytečně dostával opakované pokusy)."""
        sub = Subscription(
            id="sub_" + secrets.token_hex(6),
            callback_url=callback_url,
            floor=floor,
            secret=secrets.token_hex(32),  # 32 náhodných bajtů z kryptografického generátoru
            created_at=utc_now_iso(),
        )
        with self._lock:
            for old_id in [i for i, s in self._subs.items() if s.callback_url == callback_url]:
                del self._subs[old_id]
            self._subs[sub.id] = sub
        return sub

    def all(self) -> list[Subscription]:
        with self._lock:
            return list(self._subs.values())

    def delete(self, sub_id: str) -> bool:
        with self._lock:
            return self._subs.pop(sub_id, None) is not None

    def for_floor(self, floor: int) -> list[Subscription]:
        """Odběry, kterých se týká hlas z daného patra: stejné patro, nebo floor = null (všechna patra)."""
        with self._lock:
            return [s for s in self._subs.values() if s.floor is None or s.floor == floor]

    def report(self, sub_id: str, ok: bool) -> bool:
        """Zaznamená výsledek doručení. Vrací True, pokud byl odběr kvůli opakovaným selháním zrušen."""
        with self._lock:
            sub = self._subs.get(sub_id)
            if sub is None:
                return False
            if ok:
                sub.failures = 0
                return False
            sub.failures += 1
            limit = config.max_delivery_failures()
            if limit and sub.failures >= limit:
                del self._subs[sub_id]
                return True
            return False


votes = VoteStore()
subscriptions = SubscriptionStore()
