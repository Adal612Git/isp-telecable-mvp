"""Herramienta ligera para diagnosticar disponibilidad de puertos.

Ejemplo:
    python scripts/port_helper.py --check 3000 3001 4000
"""
from __future__ import annotations

import argparse
import socket
from typing import List


def check_ports(ports: List[int]) -> None:
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", port))
            status = "LIBRE" if result != 0 else "OCUPADO"
            print(f"Puerto {port}: {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Herramienta de diagnóstico de puertos")
    parser.add_argument("--check", nargs="+", type=int, required=True, help="Lista de puertos a verificar")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_ports(args.check)


if __name__ == "__main__":  # pragma: no cover
    main()
