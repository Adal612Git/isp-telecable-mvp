import time
import requests


import os
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
