import requests


import os
BASE = f"http://localhost:{os.getenv('HOST_CATALOGO_PORT','8001')}"


def test_planes_por_zona_y_velocidad():
    r = requests.get(f"{BASE}/planes", params={"zona": "SUR", "velocidad": 100})
    assert r.status_code == 200
    planes = r.json()
    assert all(p["velocidad"] >= 100 for p in planes)
    # SUR factor is 1.1 so price of INT100 should be 299 * 1.1
    target = next((p for p in planes if p["codigo"] == "INT100"), None)
    if target:
        assert abs(target["precio"] - 328.9) < 0.01
