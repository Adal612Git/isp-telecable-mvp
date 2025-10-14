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
BASE = f"http://localhost:{os.getenv('HOST_RED_PORT','8020')}"


def test_corte_idempotente():
    headers = {"Idempotency-Key": "cut-1"}
    r1 = requests.post(f"{BASE}/router/cortar", json={"cliente_id": 1}, headers=headers)
    assert r1.status_code == 200
    r2 = requests.post(f"{BASE}/router/cortar", json={"cliente_id": 1}, headers=headers)
    assert r2.status_code == 200
    assert r2.json().get('replay') == True

