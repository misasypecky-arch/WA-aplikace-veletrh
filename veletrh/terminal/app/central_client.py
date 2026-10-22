"""Klient centrály: přihlášení odběru, snapshot statistiky, zrušení odběru."""

import httpx


class CentralClient:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def subscribe(self, callback_url: str, floor: int | None) -> tuple[str, str]:
        """POST /api/v1/subscriptions -> (id, secret). Secret se vrací jen jednou."""
        r = await self._http.post("/api/v1/subscriptions", json={"callback_url": callback_url, "floor": floor})
        r.raise_for_status()
        data = r.json()
        return data["id"], data["secret"]

    async def snapshot(self, floor: int) -> dict:
        """GET /api/v1/stats?floor=N"""
        r = await self._http.get("/api/v1/stats", params={"floor": floor})
        r.raise_for_status()
        return r.json()

    async def unsubscribe(self, subscription_id: str) -> None:
        """DELETE /api/v1/subscriptions/{id}; 404 (odběr už neexistuje) nevadí."""
        r = await self._http.delete(f"/api/v1/subscriptions/{subscription_id}")
        if r.status_code not in (204, 404):
            r.raise_for_status()

    async def aclose(self) -> None:
        await self._http.aclose()
