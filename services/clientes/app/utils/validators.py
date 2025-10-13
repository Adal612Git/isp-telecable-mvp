import re


RFC_REGEX = re.compile(r"^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$", re.IGNORECASE)
PHONE_REGEX = re.compile(r"^\+?\d{10,15}$")


def validate_rfc(rfc: str) -> bool:
    return bool(RFC_REGEX.match(rfc.strip()))


def validate_phone(phone: str) -> bool:
    phone = phone.replace(" ", "").replace("-", "")
    return bool(PHONE_REGEX.match(phone))

