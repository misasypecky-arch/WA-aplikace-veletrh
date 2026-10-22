import os

from dotenv import load_dotenv

load_dotenv()


def central_url() -> str:
    return os.environ.get("CENTRAL_URL", "http://localhost:8080").rstrip("/")


def callback_url() -> str:
    """Adresa, na kterou centrála posílá webhooky. Buď přímo CALLBACK_URL, nebo {MY_URL}/webhooks/votes."""
    explicit = os.environ.get("CALLBACK_URL")
    if explicit:
        return explicit
    my_url = os.environ.get("MY_URL")
    if my_url:
        return my_url.rstrip("/") + "/webhooks/votes"
    return "http://localhost:8081/webhooks/votes"


def floor() -> int:
    return int(os.environ.get("FLOOR", "2"))


def poll_interval() -> float:
    """POLL_INTERVAL > 0 zapne polling (#05, jen na ukázku). 0 = vypnuto, terminál používá odběr + webhooky."""
    return float(os.environ.get("POLL_INTERVAL", "0"))


def retry_delay() -> float:
    """Za jak dlouho zkusit znovu, když se nedaří připojit k centrále."""
    return float(os.environ.get("RETRY_DELAY", "5"))
