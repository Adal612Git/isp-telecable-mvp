import os
from pathlib import Path
import time
import pathlib
import requests
import pytest


def _ensure_sample_csv(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "cliente_id,plan_id,monto,folio_interno\n"
            "1,1,350.00,CFDI-TEST-001\n"
            "2,2,499.00,CFDI-TEST-002\n"
            "3,3,199.00,CFDI-TEST-003\n"
        )


def _load_env_ports():
    p = Path('.env.ports')
    if not p.exists():
        return
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if k and (k not in os.environ):
                os.environ[k.strip()] = v.strip()
    except Exception:
        pass


@pytest.mark.integration
def test_lote_facturacion_smoke():
    """Smoke test que valida POST /facturacion/lote contra el servicio en docker.
    Requiere que el servicio esté arriba (docker-compose) y HOST_FACTURACION_PORT configurado.
    """
    _load_env_ports()
    port = os.environ.get("HOST_FACTURACION_PORT", "8003")
    base = f"http://localhost:{port}"
    url = f"{base}/facturacion/lote"

    # Crear CSV de prueba en /tmp
    csv_path = "/tmp/lote_test.csv"
    _ensure_sample_csv(csv_path)

    with open(csv_path, "rb") as fh:
        files = {"file": ("lote_test.csv", fh, "text/csv")}
        resp = requests.post(url, files=files, timeout=30)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["procesados"] == 3
    assert data["exitosos"] == 3
    assert data["fallidos"] == 0
    assert "csv_resultado" in data and data["csv_resultado"].endswith(".csv")

    # Verificación básica del nombre de archivo
    # La verificación de existencia real se hace dentro del contenedor del servicio.
    # Se deja como smoke check del nombre.
