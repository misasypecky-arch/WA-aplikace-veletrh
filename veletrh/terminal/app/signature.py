"""Ověření X-Signature = sha256=<hex HMAC-SHA256 surových bajtů těla>."""

import hashlib
import hmac

PREFIX = "sha256="


def compute(secret: str, body: bytes) -> str:
    return PREFIX + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify(secret: str, body: bytes, header: str | None) -> bool:
    """Porovná podpis v konstantním čase (hmac.compare_digest), aby se z doby odpovědi nedal podpis hádat.
    Body musí být SUROVÉ bajty požadavku, ne znovu zserializovaný JSON."""
    if not header:
        return False
    given = header.strip().lower()
    if not given.startswith(PREFIX):
        given = PREFIX + given  # tolerujeme i holý hex
    return hmac.compare_digest(compute(secret, body).encode("ascii"), given.encode("utf-8"))
