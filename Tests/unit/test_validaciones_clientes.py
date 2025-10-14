import re
from services.clientes.app.utils.validators import validate_rfc, validate_phone


def test_rfc_valido():
    assert validate_rfc("AAA010101AAA")
    assert validate_rfc("GODE561231GR8")


def test_rfc_invalido():
    assert not validate_rfc("INVALIDO")
    assert not validate_rfc("AAA010101")


def test_telefono_valido():
    assert validate_phone("5555555555")
    assert validate_phone("+525555555555")


def test_telefono_invalido():
    assert not validate_phone("123")
    assert not validate_phone("abc-def-ghij")

