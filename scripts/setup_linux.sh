#!/usr/bin/env bash
# Orquestador inteligente para Linux.
# Este wrapper garantiza que Python 3.10+ esté disponible y luego ejecuta el
# script principal en Python con los mismos argumentos que reciba.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="python3"

check_python_version() {
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3 no está instalado. Intentaré instalar python3.10 con apt." >&2
    if command -v sudo >/dev/null 2>&1; then
      read -r -p "¿Deseas continuar con la instalación? [Y/n] " answer
      answer=${answer:-Y}
      if [[ "$answer" =~ ^[Yy]$ ]]; then
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
      else
        echo "Instala manualmente Python 3.10 y vuelve a ejecutar." >&2
        exit 1
      fi
    else
      echo "Instala manualmente Python 3.10+ (sudo apt install python3)." >&2
      exit 1
    fi
  fi

  version_output="$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  major=$(echo "$version_output" | cut -d'.' -f1)
  minor=$(echo "$version_output" | cut -d'.' -f2)
  if (( major < 3 || (major == 3 && minor < 10) )); then
    echo "Se requiere Python 3.10+. Versión actual: $version_output" >&2
    exit 1
  fi
}

keep_terminal_open() {
  echo "\nEjecución finalizada. Presiona ENTER para cerrar..."
  read -r _
}

main() {
  check_python_version
  cd "$REPO_DIR"
  "$PYTHON_BIN" scripts/setup_orchestrator.py "$@"
  status=$?
  if [[ $status -ne 0 ]]; then
    echo "El orquestador finalizó con código $status." >&2
  fi
  keep_terminal_open
  exit $status
}

main "$@"
