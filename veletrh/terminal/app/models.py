"""Tvar webhooku vote.created a statistiky terminálu."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


class VoteEventData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stand_id: str
    title: str | None = None
    floor: int | None = None
    username: str | None = None
    rating: StrictInt = Field(ge=1, le=5)
    favorite: StrictBool = False


class WebhookEvent(BaseModel):
    """Obálka události: {"id", "type", "created_at", "data": {...}}.
    Pro kompatibilitu s jinými centrálami se přijme i „plochý“ tvar bez `data`."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    type: str = "vote.created"
    created_at: str | None = None
    data: VoteEventData

    @model_validator(mode="before")
    @classmethod
    def _accept_flat(cls, v):
        if isinstance(v, dict) and "data" not in v and "stand_id" in v:
            return {**v, "data": v}
        return v


class StandRow(BaseModel):
    stand_id: str = Field(examples=["S201"])
    title: str = Field(examples=["Rezervační systém pro školní učebny"])
    votes: int = Field(examples=[2])
    avg_rating: float = Field(examples=[4.5])
    favorites: int = Field(examples=[1])


class TerminalStats(BaseModel):
    """Co terminál právě zobrazuje, seřazeno podle průměru."""

    floor: int = Field(examples=[2])
    total_votes: int = Field(examples=[3])
    stands: list[StandRow]


class Status(BaseModel):
    floor: int
    loaded: bool = Field(description="Má terminál už počáteční data z centrály (snapshot)?")
    subscribed: bool = Field(description="Je terminál přihlášen k odběru událostí?")
    mode: str = Field(description="`webhooks` nebo `polling`.")
