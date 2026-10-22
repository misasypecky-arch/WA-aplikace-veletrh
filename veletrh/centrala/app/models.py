from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator


class Stand(BaseModel):
    """Jeden stánek (projekt) na veletrhu."""

    id: str = Field(description="Identifikátor stánku, součást URL v QR kódu.", examples=["S201"])
    title: str = Field(description="Název projektu.", examples=["Rezervační systém pro školní učebny"])
    authors: list[str] = Field(description="Autoři projektu.", examples=[["Marek Horák"]])
    class_name: str = Field(description="Třída autorů.", examples=["C4a"])
    floor: int = Field(description="Patro, kde stánek stojí.", examples=[2])
    room: str = Field(description="Číslo místnosti.", examples=["201"])


# ---------------------------------------------------------------- #03 Hlasy

# Písmena (i s diakritikou), číslice, tečka, podtržítko, pomlčka; 3–32 znaků.
USERNAME_PATTERN = r"^[\w.\-]{3,32}$"


class VoteIn(BaseModel):
    """Hlas žáka pro jeden stánek. Pravidla jsou popsána tady, takže validace i dokumentace jsou na jednom místě."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"username": "novak.jan", "rating": 5, "favorite": True}]},
    )

    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=USERNAME_PATTERN,
        description="Uživatelské jméno: 3–32 znaků (písmena, číslice, `.`, `_`, `-`). "
        "Jeden žák může pro stánek hlasovat jen jednou; velká a malá písmena se nerozlišují.",
        examples=["novak.jan"],
    )
    rating: StrictInt = Field(ge=1, le=5, description="Hodnocení 1 (nejhorší) až 5 (nejlepší).", examples=[5])
    favorite: StrictBool = Field(default=False, description="Je to můj favorit?", examples=[True])


class VoteOut(BaseModel):
    """Uložený hlas."""

    stand_id: str = Field(examples=["S201"])
    username: str = Field(examples=["novak.jan"])
    rating: int = Field(examples=[5])
    favorite: bool = Field(examples=[True])
    created_at: str = Field(description="Čas uložení, UTC, ISO 8601.", examples=["2026-10-22T08:15:00.123456Z"])


# ------------------------------------------------------------- #04 Statistika


class StandStats(BaseModel):
    """Statistika jednoho stánku."""

    stand_id: str = Field(examples=["S201"])
    title: str = Field(examples=["Rezervační systém pro školní učebny"])
    floor: int = Field(examples=[2])
    votes: int = Field(description="Počet hlasů.", examples=[2])
    rating_sum: int = Field(description="Součet hodnocení (z něj lze po každém hlasu přepočítat průměr).", examples=[9])
    avg_rating: float = Field(description="Průměrné hodnocení; 0.0, pokud stánek nemá žádný hlas.", examples=[4.5])
    favorites: int = Field(description="Kolikrát byl stánek označen jako favorit.", examples=[1])


class Stats(BaseModel):
    """Statistika všech stánků (případně jen jednoho patra)."""

    generated_at: str = Field(description="Okamžik výpočtu, UTC, ISO 8601.", examples=["2026-10-22T08:15:00.000000Z"])
    total_votes: int = Field(examples=[3])
    stands: list[StandStats]


# --------------------------------------------------------------- #06 Odběry


class SubscriptionIn(BaseModel):
    """Přihlášení terminálu k odběru událostí."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"callback_url": "http://10.0.0.21:8081/webhooks/votes", "floor": 2}]}
    )

    callback_url: str = Field(
        description="Adresa terminálu, na kterou má centrála POSTovat události (viz callback `vote.created`).",
        examples=["http://10.0.0.21:8081/webhooks/votes"],
    )
    floor: int | None = Field(
        default=None,
        ge=0,
        description="Patro, které terminál zajímá. `null` = všechna patra.",
        examples=[2],
    )

    @field_validator("callback_url")
    @classmethod
    def _valid_url(cls, v: str) -> str:
        p = urlparse(v)
        if p.scheme not in ("http", "https") or not p.netloc:
            raise ValueError("callback_url musí být platná adresa http:// nebo https://")
        return v


class SubscriptionOut(BaseModel):
    """Odběr bez tajného klíče (takto vypadá v seznamu)."""

    id: str = Field(examples=["sub_3fa85f64a1b2"])
    callback_url: str = Field(examples=["http://10.0.0.21:8081/webhooks/votes"])
    floor: int | None = Field(examples=[2])
    created_at: str = Field(examples=["2026-10-22T08:00:00.000000Z"])


class SubscriptionCreated(SubscriptionOut):
    """Odpověď na přihlášení – jediný okamžik, kdy se `secret` vrací."""

    secret: str = Field(
        description="Tajný klíč (32 náhodných bajtů, hex). Slouží k ověření `X-Signature`. Už se nikdy nevrátí.",
        examples=["9f2c…64 hex znaků…"],
    )


# ------------------------------------------------------ #07 Tvar webhooku


class VoteEventData(BaseModel):
    stand_id: str = Field(examples=["S201"])
    title: str = Field(examples=["Rezervační systém pro školní učebny"])
    floor: int = Field(examples=[2])
    username: str = Field(examples=["novak.jan"])
    rating: int = Field(examples=[5])
    favorite: bool = Field(examples=[True])


class VoteEvent(BaseModel):
    """Tělo webhooku `vote.created`."""

    id: str = Field(description="Id události (stejné i při opakovaném doručení).", examples=["evt_5c1e0b7a…"])
    type: str = Field(description="Typ události.", examples=["vote.created"])
    created_at: str = Field(description="Čas uložení hlasu, UTC, ISO 8601.", examples=["2026-10-22T08:15:00.123456Z"])
    data: VoteEventData
