import os

from dotenv import load_dotenv

load_dotenv()


def central_url() -> str:
    return os.environ.get("CENTRAL_URL", "http://localhost:8080").rstrip("/")


def callback_url() -> str:
    return os.environ.get("CALLBACK_URL", "http://localhost:8081/webhooks/votes")


def floor() -> int:
    return int(os.environ.get("FLOOR", "2"))
