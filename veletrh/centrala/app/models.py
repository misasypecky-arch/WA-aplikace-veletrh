from pydantic import BaseModel, Field


class Stand(BaseModel):
    """Jeden stánek (projekt) na veletrhu."""

    id: str = Field(description="Identifikátor stánku, součást URL v QR kódu.", examples=["S201"])
    title: str = Field(description="Název projektu.", examples=["Rezervační systém pro školní učebny"])
    authors: list[str] = Field(description="Autoři projektu.", examples=[["Marek Horák"]])
    class_name: str = Field(description="Třída autorů.", examples=["C4a"])
    floor: int = Field(description="Patro, kde stánek stojí.", examples=[2])
    room: str = Field(description="Číslo místnosti.", examples=["201"])
