import unicodedata
import logging

logger = logging.getLogger(__name__)

COUNTRY_ALIASES = {
    "mexico": "mexico",
    "mx": "mexico",
    "mxn": "mexico",
    "colombia": "colombia",
    "co": "colombia",
    "argentina": "argentina",
    "ar": "argentina",
    "espana": "espana",
    "spain": "espana",
    "es": "espana",
    "chile": "chile",
    "cl": "chile",
    "peru": "peru",
    "pe": "peru",
}

DEVICE_ALIASES = {
    "mobile": "Mobile",
    "movil": "Mobile",
    "celular": "Mobile",
    "cel": "Mobile",
    "smartphone": "Mobile",
    "telefono": "Mobile",
    "desktop": "Desktop",
    "escritorio": "Desktop",
    "pc": "Desktop",
    "laptop": "Desktop",
    "computador": "Desktop",
    "web": "Desktop",
}


def strip_accents(value: str) -> str:
    """Elimina diacrÃ­ticos: 'MÃ©xico' -> 'Mexico', 'PerÃº' -> 'Peru'."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", without_marks)


def _fold(value: str) -> str:
    return strip_accents(str(value or "")).strip().lower()


def normalize_country(value: str | None) -> str | None:
    """
    Normaliza un nombre de paÃ­s a su clave canÃ³nica sin acentos.
    Retorna None si la entrada es vacÃ­a, para no aplicar un filtro accidental.
    """
    if value is None:
        return None
    folded = _fold(value)
    if not folded:
        return None
    return COUNTRY_ALIASES.get(folded, folded)


def normalize_device(value: str | None) -> str | None:
    """Normaliza un dispositivo a 'Mobile', 'Desktop' o None."""
    if value is None:
        return None
    folded = _fold(value)
    if not folded:
        return None
    if folded in DEVICE_ALIASES:
        return DEVICE_ALIASES[folded]
    if "mobile" in folded or "movil" in folded or "cel" in folded:
        return "Mobile"
    return "Desktop"


def match_country(value: str, target: str) -> bool:
    """
    Compara dos paÃ­ses por su forma normalizada.

    Exacta por defecto: 'mexico' NO coincide con 'mexico city' ni con
    'colombia', evitando el falso positivo del matching por subcadena que
    hacÃ­a que 'per' apareciera tambiÃ©n en otros paÃ­ses.
    """
    return normalize_country(value) == normalize_country(target)


def match_device(value: str, target: str) -> bool:
    return normalize_device(value) == normalize_device(target)