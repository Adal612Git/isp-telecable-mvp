"""Orquestador de setup inteligente para ISP Telecable MVP.

Este módulo implementa un sistema multiplataforma que guía a la persona usuaria
para preparar, verificar y ejecutar la demo del proyecto. El enfoque es
explicativo, resiliente a fallos y persistente en la recopilación del estado
actual de la máquina.

El flujo general está dividido en etapas numeradas que pueden reintentarse con
retroceso exponencial. Para cada etapa se muestra un tablero en consola (usando
``rich`` si está disponible) y se registran los eventos en ``logs/setup.log``.

La implementación está pensada para ejecutarse tanto en modo interactivo como en
modo automático (``--yes`` o ``--ci``). En modo interactivo se pregunta antes de
instalar paquetes o ejecutar comandos potencialmente disruptivos. Si una
instalación automática no está disponible, se muestran instrucciones detalladas
para ejecutarla manualmente.

Principales características:

* Detección de sistema operativo y versión de Python.
* Verificación e instalación (cuando es posible) de dependencias críticas como
  Docker, Node.js, pnpm/npm, Git y Playwright.
* Gestión robusta de puertos con escritura/actualización de ``.env.ports``.
* Lanzamiento opcional de servicios vía ``docker compose`` y procesos Node.
* Health checks repetidos con retroceso exponencial y opción de demo automática.
* Persistencia del estado reciente en ``logs/last_state.json``.

El script prioriza la claridad: cada mensaje informa qué se está haciendo, qué
falló (en caso de error) y cómo solucionarlo.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, IO, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
except ImportError:  # pragma: no cover - fallback cuando rich no está disponible
    Console = None  # type: ignore

# --------------------------- Configuración global --------------------------- #

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "setup.log"
LAST_STATE_FILE = LOG_DIR / "last_state.json"
DEMO_TRANSCRIPT_FILE = LOG_DIR / "demo_transcript.txt"
PORTS_FILE = Path(".env.ports")
DEFAULT_PORT_RANGE = "3000-3999"

SERVICE_PORT_HINTS: Dict[str, int] = {
    "HOST_CLIENTES_PORT": 3000,
    "HOST_TECH_PORT": 3001,
    "HOST_SALES_PORT": 3002,
    "HOST_ROUTER_SIM_PORT": 4000,
    "HOST_CLIENTES_API_PORT": 8000,
    "HOST_FACTURACION_API_PORT": 8001,
    "HOST_FRONTEND_ADMIN_PORT": 4173,
}

DEPENDENCY_COMMANDS: Dict[str, List[str]] = {
    "docker": ["docker", "--version"],
    "docker-compose": ["docker", "compose", "version"],
    "node": ["node", "--version"],
    "pnpm": ["pnpm", "--version"],
    "npm": ["npm", "--version"],
    "python": [sys.executable, "--version"],
    "pip": [sys.executable, "-m", "pip", "--version"],
    "playwright": ["npx", "playwright", "--version"],
    "git": ["git", "--version"],
}

OPTIONAL_PYTHON_DEPENDENCIES = [
    "requests",
    "psutil",
    "rich",
    "websocket-client",
    "python-dotenv",
]

StageCallable = Callable[[], "StageResult"]


@dataclass
class StageResult:
    """Resultado de la ejecución de una etapa del orquestador."""

    success: bool
    message: str
    actions: List[str] = field(default_factory=list)
    auto_fix: Optional[Callable[[], None]] = None
    diagnostic: Optional[str] = None
    data: Dict[str, object] = field(default_factory=dict)


class SetupOrchestrator:
    """Orquestador principal que ejecuta las etapas y gestiona la interacción."""

    def __init__(
        self,
        auto_confirm: bool = False,
        demo_mode: bool = False,
        ci_mode: bool = False,
        verbose: bool = False,
    ) -> None:
        self.auto_confirm = auto_confirm or ci_mode
        self.demo_mode = demo_mode
        self.ci_mode = ci_mode
        self.verbose = verbose
        self.console = Console() if Console else None
        self.logger = self._configure_logging()
        self.os_name = platform.system().lower()
        self.state: Dict[str, object] = {
            "stages": {},
            "timestamp": time.time(),
            "os": self.os_name,
        }
        self.background_processes: List[Tuple[subprocess.Popen, Optional[IO[str]]]] = []
        self.started_apps: set[str] = set()
        self.failed_stages: List[str] = []
        self.skipped_stages: List[str] = []
        self._ensure_python_packages()
        self.logger.debug("Instancia de SetupOrchestrator creada")

    # ---------------------------- Utilidades base ---------------------------- #

    def _configure_logging(self) -> logging.Logger:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
            backup = LOG_DIR / "setup.log.1"
            if backup.exists():
                backup.unlink()
            LOG_FILE.rename(backup)
        logger = logging.getLogger("setup_orchestrator")
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if self.verbose:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger

    def _ensure_python_packages(self) -> None:
        """Verifica que las dependencias Python estén instaladas e intenta instalarlas."""

        missing: List[str] = []
        for package in OPTIONAL_PYTHON_DEPENDENCIES:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if not missing:
            return

        self._emit(
            "🔍 Verificando dependencias Python...")
        self.logger.info("Dependencias Python faltantes: %s", ", ".join(missing))
        if not self.auto_confirm:
            respuesta = self._prompt(
                textwrap.dedent(
                    f"""
                    Se requieren los paquetes Python: {', '.join(missing)}.
                    ¿Deseas que intente instalarlos usando pip?
                    Comando sugerido: {sys.executable} -m pip install {' '.join(missing)}
                    [Y/n]
                    """
                ).strip(),
                default="y",
            )
            if respuesta.lower() not in {"y", "yes", ""}:
                self._emit(
                    "❗ No se instalaron automáticamente. Instala manualmente antes de continuar.")
                return
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing]
            )
            self._emit("✅ Dependencias Python instaladas correctamente.")
            self.logger.info("Instalación pip exitosa")
        except subprocess.CalledProcessError as exc:
            self.logger.error("Fallo al instalar dependencias Python: %s", exc)
            self._emit(
                "⚠️ No fue posible instalar dependencias automáticamente. Ejecuta el comando"
                f" manualmente y vuelve a intentar."
            )

    def _emit(self, message: str) -> None:
        if self.console:
            self.console.print(message)
        else:
            print(message)
        self.logger.info(message)

    def _prompt(self, prompt: str, default: str = "") -> str:
        if self.auto_confirm:
            self.logger.debug("Auto confirmación activada, devolviendo default=%s", default)
            return default
        try:
            return input(f"{prompt}\n> ") or default
        except KeyboardInterrupt:
            self.logger.warning("Entrada cancelada por el usuario")
            raise SystemExit(1) from None

    def _save_state(self) -> None:
        self.state["timestamp"] = time.time()
        LAST_STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _run_command(
        self,
        command: Iterable[str],
        check: bool = False,
        capture: bool = False,
        shell: bool = False,
    ) -> subprocess.CompletedProcess:
        """Ejecuta un comando con logging detallado."""

        cmd_display = command if isinstance(command, str) else " ".join(command)
        self.logger.debug("Ejecutando comando: %s", cmd_display)
        stdout_setting = subprocess.PIPE if capture else None
        stderr_setting = subprocess.STDOUT if capture else None
        completed = subprocess.run(
            command,
            check=check,
            capture_output=capture,
            stdout=stdout_setting,
            stderr=stderr_setting,
            text=True,
            shell=shell,
        )
        if capture and completed.stdout:
            self.logger.debug("Salida: %s", completed.stdout.strip())
        return completed

    # ----------------------------- Ejecución total ---------------------------- #

    def run(self) -> None:
        self._emit("INICIANDO SETUP INTELIGENTE — ISP TELECABLE MVP")
        stages: List[Tuple[str, StageCallable]] = [
            ("Etapa 0 · Validación pre-check", self.stage_precheck),
            ("Etapa 1 · Dependencias runtime", self.stage_dependencies),
            ("Etapa 2 · Archivos de configuración", self.stage_config_files),
            ("Etapa 3 · Puertos y .env.ports", self.stage_ports),
            ("Etapa 4 · Arranque de servicios", self.stage_start_services),
            ("Etapa 5 · Health checks", self.stage_health_checks),
        ]
        if self.demo_mode:
            stages.append(("Etapa 6 · Demo automática", self.stage_demo))

        for name, stage_callable in stages:
            self._execute_stage(name, stage_callable)
            self._save_state()

        self._emit(
            "LISTO ✅ El demo está corriendo (si todas las etapas finalizaron)."
            " URLs y detalles en logs/setup.log. Presiona ENTER para cerrar.")
        if self.failed_stages:
            self._emit(
                f"Etapas con error: {', '.join(self.failed_stages)}. Revisa logs/setup.log para más detalles."
            )
        if self.skipped_stages:
            self._emit(
                f"Etapas omitidas manualmente: {', '.join(self.skipped_stages)}."
            )
        if not self.auto_confirm and not self.ci_mode:
            input()
        self._terminate_background_processes()
        if self.ci_mode:
            if self.failed_stages:
                raise SystemExit(2)
            if self.skipped_stages:
                raise SystemExit(1)

    def _execute_stage(self, name: str, stage_callable: StageCallable) -> None:
        self._emit(f"Iniciando {name}...")
        backoff = 5
        attempts = 0
        last_result = StageResult(success=False, message="")
        while True:
            attempts += 1
            result = stage_callable()
            last_result = result
            self.state.setdefault("stages", {})[name] = {
                "success": result.success,
                "message": result.message,
                "attempts": attempts,
                "data": result.data,
            }
            self._present_stage_result(name, result, attempts)
            if result.success:
                break
            if self.ci_mode:
                self.failed_stages.append(name)
                break
            action = self._choose_action(result)
            if action == "skip":
                self.skipped_stages.append(name)
                break
            if action == "quit":
                self._terminate_background_processes()
                raise SystemExit(1)
            if action == "auto" and result.auto_fix:
                try:
                    result.auto_fix()
                except Exception as exc:  # pragma: no cover - defensa adicional
                    self.logger.exception("Auto-fix falló: %s", exc)
                    self._emit(f"⚠️ Auto-fix falló: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        if not last_result.success and name not in self.failed_stages and name not in self.skipped_stages:
            self.failed_stages.append(name)

    def _present_stage_result(self, name: str, result: StageResult, attempts: int) -> None:
        status = "✅" if result.success else "❌"
        summary = f"{status} {name} — {result.message} (intentos: {attempts})"
        if self.console:
            panel = Panel(Text(summary))
            self.console.print(panel)
            if result.diagnostic:
                self.console.print(Panel(result.diagnostic, title="Diagnóstico"))
            if result.actions:
                table = Table(title="Siguientes pasos sugeridos")
                table.add_column("Acción")
                for action in result.actions:
                    table.add_row(action)
                self.console.print(table)
        else:
            print(summary)
            if result.diagnostic:
                print(result.diagnostic)
            if result.actions:
                print("Siguientes pasos:")
                for action in result.actions:
                    print(f" - {action}")
        self.logger.info(summary)
        if result.diagnostic:
            self.logger.info(result.diagnostic)
        for action in result.actions:
            self.logger.info("Sugerencia: %s", action)

    def _choose_action(self, result: StageResult) -> str:
        if result.success:
            return "continue"
        options = {
            "r": "Reintentar",
            "a": "Auto-fix" if result.auto_fix else None,
            "s": "Saltar",
            "q": "Salir",
        }
        options = {k: v for k, v in options.items() if v}
        prompt_lines = ["Selecciona una opción:"]
        for key, label in options.items():
            prompt_lines.append(f"  ({key.upper()}) {label}")
        prompt = "\n".join(prompt_lines)

        if self.auto_confirm:
            if result.auto_fix:
                self.logger.debug("Auto confirm: ejecutando auto-fix")
                return "auto"
            return "retry"

        choice = self._prompt(prompt, default="r").lower()
        mapping = {"r": "retry", "a": "auto", "s": "skip", "q": "quit"}
        return mapping.get(choice, "retry")

    def _terminate_background_processes(self) -> None:
        for proc, log_file in self.background_processes:
            if proc.poll() is None:
                self.logger.info("Terminando proceso %s", proc.pid)
                try:
                    proc.terminate()
                except Exception:  # pragma: no cover - defensa
                    pass
            if log_file:
                try:
                    log_file.close()
                except Exception:  # pragma: no cover - defensa
                    pass

    # ----------------------------- Etapa 0 ---------------------------------- #

    def stage_precheck(self) -> StageResult:
        diagnostics: List[str] = []
        actions: List[str] = []

        python_version = sys.version.split()[0]
        if sys.version_info < (3, 10):
            diagnostics.append(
                f"Python detectado: {python_version}. Se requiere 3.10 o superior." )
            actions.append(
                "Instala Python 3.10+: https://www.python.org/downloads/"
            )
            return StageResult(
                success=False,
                message="Python desactualizado",
                diagnostic="\n".join(diagnostics),
                actions=actions,
            )

        git_path = shutil.which("git")
        if not git_path:
            diagnostics.append("Git no encontrado en PATH.")
            actions.append("Instala Git: sudo apt install git / winget install Git.Git")
            return StageResult(
                success=False,
                message="Git no disponible",
                diagnostic="\n".join(diagnostics),
                actions=actions,
            )

        repo_dirty = self._run_command(["git", "status", "--short"], capture=True)
        self.logger.debug("git status --short => %s", repo_dirty.stdout)

        return StageResult(
            success=True,
            message=f"Python {python_version} y Git disponibles.",
            data={"python_version": python_version, "git": git_path},
        )

    # ----------------------------- Etapa 1 ---------------------------------- #

    def stage_dependencies(self) -> StageResult:
        missing: List[str] = []
        diagnostics: List[str] = []

        for dep, cmd in DEPENDENCY_COMMANDS.items():
            if shutil.which(cmd[0]) is None:
                missing.append(dep)
                diagnostics.append(f"{dep} no está instalado o no está en PATH.")
            else:
                result = self._run_command(cmd, capture=True)
                if result.returncode != 0:
                    diagnostics.append(f"{dep} respondió con código {result.returncode}.")
                    missing.append(dep)
                else:
                    diagnostics.append(f"{dep}: {result.stdout.strip() if result.stdout else 'OK'}")

        if missing:
            install_message = self._dependency_install_instructions(missing)

            def auto_fix() -> None:
                self._attempt_dependency_installation(missing)

            return StageResult(
                success=False,
                message="Faltan dependencias críticas.",
                diagnostic="\n".join(diagnostics + [install_message]),
                actions=[install_message],
                auto_fix=auto_fix,
                data={"missing": missing},
            )

        return StageResult(
            success=True,
            message="Todas las dependencias respondieron correctamente.",
            diagnostic="\n".join(diagnostics),
        )

    def _dependency_install_instructions(self, missing: List[str]) -> str:
        if "linux" in self.os_name:
            packages = " ".join(missing)
            return (
                "Comando sugerido (Ubuntu/Debian): sudo apt update && "
                f"sudo apt install -y {packages}"
            )
        if "windows" in self.os_name:
            manager = None
            if shutil.which("winget"):
                manager = "winget"
            elif shutil.which("choco"):
                manager = "choco"
            if manager == "winget":
                return (
                    "Instala dependencias con winget, ejemplo: "
                    "winget install -e --id Docker.DockerDesktop"
                )
            if manager == "choco":
                return (
                    "Instala dependencias con Chocolatey, ejemplo: "
                    "choco install docker-desktop git nodejs"
                )
            return (
                "Instala manualmente las dependencias visitando las páginas oficiales "
                "de Docker, Node.js y Git."
            )
        if "darwin" in self.os_name:
            return (
                "macOS detectado. Usa brew install docker node git o instala manualmente."
            )
        return "Instala manualmente las dependencias faltantes."

    def _attempt_dependency_installation(self, missing: List[str]) -> None:
        if "linux" not in self.os_name:
            self._emit(
                "Auto-fix solo implementado para Linux. Ejecuta las instalaciones manualmente.")
            return
        pkgs = []
        mapping = {
            "docker": "docker.io docker-compose-plugin",
            "docker-compose": "docker-compose-plugin",
            "node": "nodejs npm",
            "pnpm": "pnpm",
            "npm": "npm",
            "git": "git",
            "playwright": "playwright",
        }
        for dep in missing:
            pkgs.append(mapping.get(dep, dep))
        command = (
            "sudo apt update && sudo apt install -y " + " ".join(sorted(set(" ".join(pkgs).split())))
        )
        self._emit(
            f"Intentando instalar automáticamente: {command}. Puede requerir contraseña de sudo.")
        try:
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError as exc:
            self.logger.error("Instalación automática falló: %s", exc)
            self._emit(
                "No fue posible completar la instalación automática. Sigue las instrucciones manuales.")

    # ----------------------------- Etapa 2 ---------------------------------- #

    def stage_config_files(self) -> StageResult:
        missing_files: List[str] = []
        diagnostics: List[str] = []

        for filename in [".env", ".env.ports"]:
            file_path = Path(filename)
            if not file_path.exists():
                if filename == ".env.ports":
                    diagnostics.append(
                        ".env.ports no existe todavía; se generará durante la etapa de puertos."
                    )
                else:
                    missing_files.append(filename)
                    diagnostics.append(f"No se encontró {filename}.")
            else:
                diagnostics.append(f"{filename} encontrado.")

        critical_dirs = [Path("infra/postgres"), Path("infra/minio-data"), Path("services/router_simulator")]
        for directory in critical_dirs:
            if not directory.exists():
                diagnostics.append(f"Directorio faltante: {directory}")
                missing_files.append(str(directory))
            else:
                diagnostics.append(f"Directorio presente: {directory}")

        if missing_files:
            actions = [
                "Verifica que hayas clonado los submódulos o descargado los recursos requeridos.",
                "Si falta services/router_simulator ejecuta: git submodule update --init --recursive",
            ]
            return StageResult(
                success=False,
                message="Faltan archivos o directorios críticos.",
                diagnostic="\n".join(diagnostics),
                actions=actions,
            )

        return StageResult(
            success=True,
            message="Archivos .env y directorios críticos verificados.",
            diagnostic="\n".join(diagnostics),
        )

    # ----------------------------- Etapa 3 ---------------------------------- #

    def stage_ports(self) -> StageResult:
        range_str = os.environ.get("PORT_RANGE", DEFAULT_PORT_RANGE)
        try:
            start_str, end_str = range_str.split("-")
            start, end = int(start_str), int(end_str)
        except ValueError:
            return StageResult(
                success=False,
                message="Variable PORT_RANGE inválida.",
                actions=["Usa formato inicio-fin, por ejemplo 3000-3999."],
            )

        assigned_ports = self._assign_ports(start, end)
        if not assigned_ports:
            return StageResult(
                success=False,
                message="No se pudieron asignar puertos libres.",
                actions=[
                    "Libera puertos cerrando procesos o modifica PORT_RANGE.",
                ],
            )
        self.state["ports"] = assigned_ports
        return StageResult(
            success=True,
            message="Puertos reservados y .env.ports actualizado.",
            data={"ports": assigned_ports},
        )

    def _assign_ports(self, start: int, end: int) -> Dict[str, int]:
        assigned: Dict[str, int] = {}
        ports_content = {}
        if PORTS_FILE.exists():
            for line in PORTS_FILE.read_text().splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    ports_content[key.strip()] = int(value.strip())

        def find_free_port(preferred: int) -> Optional[int]:
            for port in range(preferred, end + 1):
                if port < start:
                    continue
                if all(port != used for used in assigned.values()):
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        result = s.connect_ex(("127.0.0.1", port))
                        if result != 0:
                            return port
            return None

        updates: List[str] = []
        for key, preferred in SERVICE_PORT_HINTS.items():
            current = ports_content.get(key, preferred)
            free_port = find_free_port(current)
            if free_port is None:
                self.logger.warning("No hay puerto disponible para %s", key)
                return {}
            assigned[key] = free_port
            updates.append(f"{key}={free_port}")

        PORTS_FILE.write_text("\n".join(updates) + "\n", encoding="utf-8")
        self._emit(f".env.ports actualizado con {len(assigned)} entradas.")
        return assigned

    # ----------------------------- Etapa 4 ---------------------------------- #

    def stage_start_services(self) -> StageResult:
        diagnostics: List[str] = []
        actions: List[str] = []

        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            command = ["docker", "compose", "up", "-d", "--build"]
            diagnostics.append("docker-compose.yml detectado. Intentando docker compose up...")

            def auto_fix() -> None:
                self._emit("Ejecutando docker compose up -d --build")
                subprocess.call(command)

            try:
                subprocess.check_call(command)
                diagnostics.append("docker compose up ejecutado correctamente.")
            except subprocess.CalledProcessError as exc:
                diagnostics.append(f"docker compose falló: {exc}")
                actions.append(
                    "Revisa Docker Desktop / servicio docker y vuelve a intentar con docker compose up -d --build"
                )
                return StageResult(
                    success=False,
                    message="docker compose no pudo levantar los servicios.",
                    diagnostic="\n".join(diagnostics),
                    actions=actions,
                    auto_fix=auto_fix,
                )
        else:
            diagnostics.append("No se encontró docker-compose.yml; se omite docker compose.")

        # Arranque de frontends/apps basados en Node
        ports = self.state.get("ports", {})
        apps_dir = Path("apps")
        if apps_dir.exists():
            for app in apps_dir.iterdir():
                package_json = app / "package.json"
                if package_json.exists():
                    port_key = None
                    for key in SERVICE_PORT_HINTS:
                        if key.lower().startswith(f"host_{app.name.replace('-', '_')}"):
                            port_key = key
                            break
                    assigned_port = ports.get(port_key) if isinstance(ports, dict) else None
                    diagnostics.append(f"Preparando {app} (puerto {assigned_port or 'por defecto'})")
                    self._start_node_app(app, assigned_port)

        return StageResult(
            success=True,
            message="Servicios iniciados o verificados.",
            diagnostic="\n".join(diagnostics),
        )

    def _start_node_app(self, app_dir: Path, port: Optional[int]) -> None:
        package_manager = None
        if shutil.which("pnpm"):
            package_manager = "pnpm"
        elif shutil.which("npm"):
            package_manager = "npm"

        if package_manager is None:
            self._emit(
                f"No se detectó npm/pnpm para {app_dir.name}. Ejecuta la instalación manualmente.")
            return

        if app_dir.name in self.started_apps:
            self._emit(f"{app_dir.name} ya está en ejecución; se omite relanzar.")
            return

        install_cmd = [package_manager, "install"]
        dev_cmd = [package_manager, "run", "dev"]
        env = os.environ.copy()
        if port:
            env.setdefault("PORT", str(port))
            env.setdefault("VITE_PORT", str(port))

        self._emit(f"Instalando dependencias de {app_dir} con {package_manager}...")
        try:
            subprocess.check_call(install_cmd, cwd=app_dir)
        except subprocess.CalledProcessError as exc:
            self.logger.error("Fallo instalando dependencias de %s: %s", app_dir, exc)
            self._emit(
                f"No se pudo instalar dependencias en {app_dir}. Revisa logs y ejecuta {package_manager} install manualmente.")
            return

        self._emit(f"Lanzando {app_dir.name} con {package_manager} run dev...")
        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / f"{app_dir.name}.service.log"
        log_file = open(log_path, "a", encoding="utf-8")
        process = subprocess.Popen(
            dev_cmd,
            cwd=app_dir,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        self.logger.info("Logs del servicio %s se guardan en %s", app_dir, log_path)
        self.background_processes.append((process, log_file))
        self.logger.info("Proceso %s iniciado para %s", process.pid, app_dir)
        self.started_apps.add(app_dir.name)

    # ----------------------------- Etapa 5 ---------------------------------- #

    def stage_health_checks(self) -> StageResult:
        ports = self.state.get("ports", {})
        if not ports:
            return StageResult(
                success=False,
                message="No se encontraron puertos asignados.",
                actions=["Ejecuta nuevamente la etapa de puertos."],
            )
        try:
            import requests
        except ImportError:
            return StageResult(
                success=False,
                message="La librería requests es necesaria para health checks.",
                actions=["Instala con pip install requests"],
            )

        endpoints = []
        for key, port in ports.items():
            if "ROUTER" in key or "API" in key:
                endpoints.append((key, f"http://localhost:{port}/health"))
        if not endpoints:
            endpoints.append(("GENERIC", "http://localhost:3000/health"))

        diagnostics: List[str] = []
        for name, url in endpoints:
            diagnostics.append(f"Comprobando {name} -> {url}")
            success = self._poll_health(url, retries=5)
            diagnostics.append("OK" if success else "FALLÓ")
            if not success:
                return StageResult(
                    success=False,
                    message=f"Endpoint {url} no responde 200.",
                    diagnostic="\n".join(diagnostics),
                    actions=["Verifica que el servicio esté corriendo y accesible."],
                )

        return StageResult(
            success=True,
            message="Todos los health checks respondieron correctamente.",
            diagnostic="\n".join(diagnostics),
        )

    def _poll_health(self, url: str, retries: int = 5, backoff: int = 5) -> bool:
        import requests

        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
                self.logger.warning("%s respondió %s", url, response.status_code)
            except requests.RequestException as exc:
                self.logger.warning("Health check error (%s): %s", url, exc)
            if self.ci_mode:
                break
            time.sleep(backoff * attempt)
        return False

    # ----------------------------- Etapa 6 ---------------------------------- #

    def stage_demo(self) -> StageResult:
        try:
            import requests
        except ImportError:
            return StageResult(
                success=False,
                message="requests es necesario para la demo automática.",
                actions=["Instala requests con pip."],
            )

        ports = self.state.get("ports", {})
        clientes_api = ports.get("HOST_CLIENTES_API_PORT") if isinstance(ports, dict) else None
        if not clientes_api:
            return StageResult(
                success=False,
                message="No se encontró puerto para clientes API.",
            )

        base_url = f"http://localhost:{clientes_api}"
        transcript_lines: List[str] = []

        def log_step(msg: str) -> None:
            transcript_lines.append(msg)
            self._emit(msg)

        log_step("Iniciando demo automática...")
        try:
            response = requests.post(
                f"{base_url}/clientes", json={"nombre": "Demo", "plan": "Familiar"}, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            router_id = data.get("router_id")
            log_step(f"Cliente demo creado. Router asignado: {router_id}")
            if router_id:
                requests.post(
                    f"{base_url}/routers/{router_id}/power",
                    json={"action": "off"},
                    timeout=10,
                )
                log_step("Router apagado (acción demo).")
                time.sleep(2)
                requests.post(
                    f"{base_url}/routers/{router_id}/power",
                    json={"action": "on"},
                    timeout=10,
                )
                log_step("Router encendido nuevamente.")
        except requests.RequestException as exc:
            self.logger.error("Demo automática falló: %s", exc)
            return StageResult(
                success=False,
                message="No se pudo completar la demo automática.",
                diagnostic=str(exc),
            )

        DEMO_TRANSCRIPT_FILE.write_text("\n".join(transcript_lines), encoding="utf-8")
        return StageResult(
            success=True,
            message="Demo automática ejecutada exitosamente.",
        )


# ------------------------------ Punto de entrada --------------------------- #


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orquestador de setup inteligente para ISP Telecable MVP",
    )
    parser.add_argument(
        "--yes",
        "--auto",
        action="store_true",
        dest="auto",
        help="Modo no interactivo (acepta acciones sugeridas automáticamente).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta la demo automática al final del setup.",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Modo CI con timeouts estrictos y sin prompts interactivos.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra logs detallados también en consola.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    orchestrator = SetupOrchestrator(
        auto_confirm=args.auto,
        demo_mode=args.demo,
        ci_mode=args.ci,
        verbose=args.verbose,
    )
    orchestrator.run()


if __name__ == "__main__":  # pragma: no cover
    main()
