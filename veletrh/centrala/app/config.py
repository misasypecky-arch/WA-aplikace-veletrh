import os

from dotenv import load_dotenv

# Načte .env (pokud existuje). Skutečné proměnné prostředí mají přednost.
load_dotenv()


def public_url() -> str:
    """Veřejná adresa centrály bez koncového lomítka. Čte se při každém volání."""
    return os.environ.get("PUBLIC_URL", "http://localhost:8080").rstrip("/")
