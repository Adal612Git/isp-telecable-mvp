import os
# Ensure DB driver not required during unit import
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from services.facturacion.app.main import generar_cfdi_xml


def test_cfdi_xml_minimo():
    xml = generar_cfdi_xml(cliente_id=1, total=123.45, uuid="UUID-TEST")
    assert "Version=\"4.0\"" in xml
    assert "UUID=\"UUID-TEST\"" in xml
    assert "Total=\"123.45\"" in xml
