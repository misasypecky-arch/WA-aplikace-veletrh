from .models import Stand

STANDS: list[Stand] = [
    Stand(id="S101", title="Kantýna bez front", authors=["Eliška Nováková", "Tomáš Kříž"],
          class_name="C3a", floor=1, room="101"),
    Stand(id="S102", title="Mapa školy pro prváky", authors=["Jan Dvořák"],
          class_name="C2b", floor=1, room="102"),
    Stand(id="S103", title="Hlídač šaten", authors=["Petra Svobodová"],
          class_name="C3b", floor=1, room="103"),
    Stand(id="S201", title="Rezervační systém pro školní učebny", authors=["Marek Horák"],
          class_name="C4a", floor=2, room="201"),
    Stand(id="S202", title="Rozvrh na displeji", authors=["Lucie Marešová", "Adam Veselý"],
          class_name="C4a", floor=2, room="202"),
    Stand(id="S203", title="Burza učebnic", authors=["Filip Pokorný"],
          class_name="C3a", floor=2, room="203"),
    Stand(id="S301", title="Měření CO2 ve třídách", authors=["Anna Bártová", "Ondřej Sedlák"],
          class_name="C4b", floor=3, room="301"),
    Stand(id="S302", title="Školní rádio online", authors=["Karolína Němcová"],
          class_name="C2a", floor=3, room="302"),
    Stand(id="S303", title="Docházka přes NFC", authors=["Vojtěch Urban"],
          class_name="C4b", floor=3, room="303"),
]
