import os
import requests


CLI = f"http://localhost:{os.getenv('HOST_CLIENTES_PORT','8000')}"
WA = f"http://localhost:{os.getenv('HOST_WHATSAPP_PORT','8011')}"


def test_rbac_admin_stats_forbidden_then_ok():
    r_forb = requests.get(f"{CLI}/admin/stats")
    assert r_forb.status_code == 403
    r_ok = requests.get(f"{CLI}/admin/stats", headers={"X-Role": "admin"})
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert "total" in body


def test_whatsapp_webhook_and_template():
    challenge = "abc123"
    r = requests.get(f"{WA}/webhook", params={"hub_verify_token": "testtoken", "hub_challenge": challenge})
    assert r.status_code == 200
    assert r.text.strip() == challenge
    r2 = requests.post(f"{WA}/send-template", json={"to": "+521111111111", "template": "bienvenida"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "sent"

