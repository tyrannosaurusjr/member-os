import re


EMAIL_WHITESPACE_RE = re.compile(r'\s+')
NAME_WHITESPACE_RE = re.compile(r'\s+')
PHONE_EXTENSION_RE = re.compile(r'(?:ext\.?|extension|x)\s*\d+\s*$', re.IGNORECASE)
NON_DIGIT_PLUS_RE = re.compile(r'[^\d+]')


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None

    normalized = EMAIL_WHITESPACE_RE.sub('', email).strip().lower()
    return normalized or None


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None

    normalized = NAME_WHITESPACE_RE.sub(' ', name).strip()
    return normalized or None


def normalize_phone(
    phone: str | None,
    *,
    default_country_code: str = '1',
) -> str | None:
    if not phone:
        return None

    stripped = PHONE_EXTENSION_RE.sub('', phone).strip()
    if not stripped:
        return None

    if stripped.startswith('00'):
        stripped = f'+{stripped[2:]}'

    if stripped.startswith('+'):
        digits = ''.join(char for char in stripped if char.isdigit())
        return f'+{digits}' if digits else None

    digits = ''.join(char for char in NON_DIGIT_PLUS_RE.sub('', stripped) if char.isdigit())
    if not digits:
        return None

    if len(digits) == 10 and default_country_code:
        return f'+{default_country_code}{digits}'

    if len(digits) == 11 and digits.startswith(default_country_code):
        return f'+{digits}'

    if 8 <= len(digits) <= 15:
        return f'+{digits}'

    return digits
