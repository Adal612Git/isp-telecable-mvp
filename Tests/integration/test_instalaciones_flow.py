import os
import requests


def _load_env_ports():
    p = '.env.ports'
    if not os.path.exists(p):
        return
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if k and (k not in os.environ):
                os.environ[k.strip()] = v.strip()


_load_env_ports()
BASE = f"http://localhost:{os.getenv('HOST_INSTALACIONES_PORT','8005')}"


def test_agendar_despachar_cerrar_instalacion():
    # Agendar
    r = requests.post(f"{BASE}/instalaciones/agendar", json={"clienteId": 1, "ventana": "9-12", "zona": "NORTE"})
    assert r.status_code == 200, r.text
    inst_id = r.json()["id"]
    # Despachar
    r2 = requests.put(f"{BASE}/instalaciones/despachar/{inst_id}")
    assert r2.status_code == 200
    # Cerrar sin evidencias -> 400
    r3 = requests.put(f"{BASE}/instalaciones/cerrar/{inst_id}", json={"evidencias": [], "notas": ""})
    assert r3.status_code == 422 or r3.status_code == 400
    # Cerrar con evidencias -> 200 (router emulado)
    r4 = requests.put(f"{BASE}/instalaciones/cerrar/{inst_id}", json={"evidencias": ["http://example/e1.png"], "notas": "ok"})
    assert r4.status_code == 200, r4.text
    assert r4.json().get("estado") == "Completada"

