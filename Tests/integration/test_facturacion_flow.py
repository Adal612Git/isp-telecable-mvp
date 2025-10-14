import time
import requests


import os
from pathlib import Path


def _load_env_ports_into_environ():
    """Load .env.ports into os.environ if present (non-intrusive).
    Keeps existing env vars; only sets missing ones.
    """
    env_path = Path(".env.ports")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and (k not in os.environ):
                os.environ[k] = v
    except Exception:
        # Best-effort: ignore parsing errors and fall back to defaults
        pass


_load_env_ports_into_environ()
BASE = f"http://localhost:{os.getenv('HOST_FACTURACION_PORT','8002')}"


def test_generar_y_consultar_factura():
    lote = [{"cliente_id": 1, "total": 123.45}]
    r = requests.post(f"{BASE}/facturacion/generar-masiva", json=lote)
    assert r.status_code == 200, r.text
    uuid = r.json()[0]["uuid"]
    # wait briefly for async timbrado
    time.sleep(1)
    r2 = requests.get(f"{BASE}/facturacion/{uuid}")
    assert r2.status_code == 200
    data = r2.json()
    assert data["estatus"] in ("pendiente", "timbrado")
