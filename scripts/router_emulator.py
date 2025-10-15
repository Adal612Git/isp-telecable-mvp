#!/usr/bin/env python3
"""
Router emulator for Telecable MVP demo.

Simulates a MikroTik device periodically reporting status to the orchestrator.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any

import requests


ORQ_HOST = os.getenv("HOST_ORQ_HOST", "localhost")
ORQ_PORT = int(os.getenv("HOST_ORQ_PORT", "8010"))
ROUTER_ID = os.getenv("ROUTER_ID", "R-001")
CLIENTE_ID = int(os.getenv("CLIENTE_ID", "1"))
INTERVAL_SECONDS = float(os.getenv("ROUTER_POLL_INTERVAL", "10"))
ENDPOINT = f"http://{ORQ_HOST}:{ORQ_PORT}/router/reconectar"


def build_payload(state: str) -> dict[str, Any]:
    velocidad = random.randint(50, 300)
    return {
        "router_id": ROUTER_ID,
        "cliente_id": CLIENTE_ID,
        "estado": state,
        "velocidad_mbps": velocidad,
    }


def next_state(prev: str | None, cycle: int) -> str:
    if cycle == 0:
        return "instalando"
    if prev == "instalando":
        return "online"
    # Demo mode toggles between online/offline
    return random.choice(["online", "offline"])


def handle_response(resp: requests.Response) -> None:
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return
    if data.get("accion") == "reset":
        print("[router] Reiniciando router...")
        time.sleep(5)


def main() -> None:
    print(f"[router] Emulador iniciando contra {ENDPOINT}")
    state: str | None = None
    cycle = 0
    session = requests.Session()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        while True:
            state = next_state(state, cycle)
            payload = build_payload(state)
            try:
                response = session.post(ENDPOINT, json=payload, headers=headers, timeout=5)
                print(f"[router] POST {payload} -> {response.status_code}")
                handle_response(response)
            except requests.RequestException as exc:
                print(f"[router] Error reportando estado: {exc}")
            cycle += 1
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[router] Emulador detenido por usuario.")


if __name__ == "__main__":
    main()
