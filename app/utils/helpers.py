"""Funciones auxiliares reutilizables (slugify, etc.)."""

import re
import unicodedata


def slugify(value: str) -> str:
    """Convierte un texto a slug URL-safe en minúsculas."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)
