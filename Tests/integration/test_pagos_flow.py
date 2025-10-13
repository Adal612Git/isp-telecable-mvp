import requests


import os
BASE = f"http://localhost:{os.getenv('HOST_PAGOS_PORT','8003')}"


def test_procesar_y_obtener_pago():
    body = {"metodo": "spei", "monto": 150.0, "referencia": "REF-INT"}
    r = requests.post(f"{BASE}/pagos/procesar", json=body, headers={"Idempotency-Key": "x-1"})
    assert r.status_code == 200
    ref = r.json()["referencia"]
    r2 = requests.get(f"{BASE}/pagos/{ref}")
    assert r2.status_code == 200
    assert r2.json()["estatus"] == "confirmado"
