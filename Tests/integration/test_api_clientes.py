import requests


import os
BASE = f"http://localhost:{os.getenv('HOST_CLIENTES_PORT','8000')}"


def test_crear_y_obtener_cliente():
    payload = {
        "nombre": "Ana Test",
        "rfc": "AAA010101AAA",
        "email": "ana@example.com",
        "telefono": "5555555555",
        "plan_id": "INT100",
        "domicilio": {"calle":"Calle 2","numero":"5","colonia":"Centro","cp":"01000","ciudad":"CDMX","estado":"CDMX","zona":"NORTE"},
        "contacto": {"nombre":"Ana","email":"ana@example.com","telefono":"5555555555"},
        "consentimiento": {"marketing": True, "terminos": True}
    }
    r = requests.post(f"{BASE}/clientes", json=payload, headers={"Idempotency-Key": "it-1"})
    assert r.status_code == 200, r.text
    data = r.json()
    rid = data["id"]
    # Replay should return 200 with idempotent header
    r_rep = requests.post(f"{BASE}/clientes", json=payload, headers={"Idempotency-Key": "it-1"})
    assert r_rep.status_code == 200
    assert r_rep.headers.get("X-Idempotent-Replay") == "true"
    r2 = requests.get(f"{BASE}/clientes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["rfc"] == "AAA010101AAA"
