"""Utilidades de sanitización para mitigar XSS en contenidos HTML."""

import re

import bleach

# Etiquetas/atributos permitidos si el contenido admite HTML básico
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "ul",
    "ol",
    "li",
    "a",
    "h1",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "code",
    "pre",
    "img",
    "span",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
    "span": ["class"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_EMPTY_RICH_RE = re.compile(
    r"^(?:\s|&nbsp;|<p>\s*(?:<br\s*/?>)?\s*</p>|<br\s*/?>)*$",
    re.IGNORECASE,
)


def sanitize_html(content: str | None) -> str | None:
    """Limpia HTML peligroso; retorna None si el contenido es vacío."""
    if content is None:
        return None
    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned


def strip_html_to_text(content: str | None) -> str:
    """Convierte HTML a texto plano (para campos de texto corto)."""
    if content is None:
        return ""
    text = bleach.clean(str(content), tags=[], strip=True)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    return " ".join(text.split()).strip()


def is_empty_rich_text(content: str | None) -> bool:
    """True si el HTML del editor no tiene texto útil."""
    if content is None:
        return True
    raw = str(content).strip()
    if not raw:
        return True
    if _EMPTY_RICH_RE.match(raw):
        return True
    return not strip_html_to_text(raw)
