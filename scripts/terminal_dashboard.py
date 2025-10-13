#!/usr/bin/env python3
"""Dashboard en terminal para monitorear endpoints y métricas en vivo.

El script ejecuta solicitudes HTTP a una lista de endpoints, calcula estadísticas
de latencia y disponibilidad en ventanas móviles y las muestra usando paneles Rich.
Puede emplearse junto con `random_metrics_service.py` o contra cualquier API real.
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import time
from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import requests
from requests import RequestException
from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclasses.dataclass
class EndpointConfig:
    """Configuración individual de una prueba HTTP."""

    name: str
    url: str
    method: str = "GET"
    timeout: float = 3.0


class EndpointStats:
    """Almacena estadísticas de la ejecución continua de un endpoint."""

    def __init__(self, config: EndpointConfig, history_seconds: float) -> None:
        self.config = config
        self.history_seconds = history_seconds
        self.samples: Deque[Tuple[float, bool, Optional[float], int]] = deque()
        self.total_ok = 0
        self.total_fail = 0
        self.last_latency_ms: Optional[float] = None
        self.last_status_code: Optional[int] = None
        self.last_error: Optional[str] = None

    def record(self, success: bool, latency_ms: Optional[float], status_code: int, error: Optional[str]) -> None:
        now = time.time()
        self.samples.append((now, success, latency_ms, status_code))
        if success:
            self.total_ok += 1
        else:
            self.total_fail += 1
        self.last_latency_ms = latency_ms
        self.last_status_code = status_code
        self.last_error = error
        self._trim(now)

    def _trim(self, now: float) -> None:
        """Elimina muestras fuera de la ventana móvil."""
        while self.samples and (now - self.samples[0][0]) > self.history_seconds:
            self.samples.popleft()

    @property
    def total_requests(self) -> int:
        return self.total_ok + self.total_fail

    def window_stats(self) -> Dict[str, Optional[float]]:
        """Calcula métricas en la ventana móvil."""
        latencies = [lat for (_, success, lat, _) in self.samples if success and lat is not None]
        successes = sum(1 for (_, success, _, _) in self.samples if success)
        total = len(self.samples)

        if latencies:
            avg = statistics.fmean(latencies)
            p95 = percentile(latencies, 95)
        else:
            avg = None
            p95 = None

        success_rate = (successes / total) * 100 if total else None
        rps = total / self.history_seconds if self.history_seconds else None

        return {
            "avg_ms": avg,
            "p95_ms": p95,
            "success_rate": success_rate,
            "rps": rps,
        }


def percentile(values: Iterable[float], p: float) -> float:
    """Calcula percentil usando interpolación simple."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No hay valores para calcular percentil.")
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[int(k)]
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return d0 + d1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dashboard interactivo con paneles Rich para monitorear endpoints HTTP."
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        metavar="NOMBRE=URL",
        help="Endpoint a monitorear (puede repetirse). Formato: nombre=url",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Segundos entre rondas de pruebas (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="Tiempo máximo de espera por respuesta HTTP en segundos.",
    )
    parser.add_argument(
        "--history",
        type=float,
        default=60.0,
        help="Ventana móvil en segundos para estadísticas (default: %(default)s).",
    )
    parser.add_argument(
        "--method",
        default="GET",
        help="Método HTTP a utilizar para todas las solicitudes (default: %(default)s).",
    )
    parser.add_argument(
        "--no-screen",
        action="store_true",
        help="Desactiva modo pantalla completa de Rich (útil para tmux/screen).",
    )
    return parser.parse_args()


def build_endpoints(args: argparse.Namespace) -> List[EndpointConfig]:
    if not args.endpoint:
        # Valores por defecto amigables con el simulador de métricas.
        return [
            EndpointConfig(name="metrics_local", url="http://localhost:9108/metrics", method=args.method, timeout=args.timeout),
            EndpointConfig(name="prometheus", url="http://localhost:9090/-/ready", method=args.method, timeout=args.timeout),
        ]

    configs: List[EndpointConfig] = []
    for definition in args.endpoint:
        try:
            name, url = definition.split("=", 1)
        except ValueError as exc:
            raise SystemExit(f"Formato inválido para --endpoint '{definition}'. Use nombre=url.") from exc
        configs.append(EndpointConfig(name=name.strip(), url=url.strip(), method=args.method, timeout=args.timeout))
    return configs


def run_probe(config: EndpointConfig) -> Tuple[bool, Optional[float], int, Optional[str]]:
    start = time.perf_counter()
    try:
        response = requests.request(config.method, config.url, timeout=config.timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        ok = response.status_code < 400
        error = None if ok else f"HTTP {response.status_code}"
        return ok, latency_ms, response.status_code, error
    except RequestException as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return False, latency_ms, 0, str(exc)


def render_header(uptime_seconds: float, endpoints: Dict[str, EndpointStats]) -> Panel:
    total_requests = sum(stats.total_requests for stats in endpoints.values())
    total_success = sum(stats.total_ok for stats in endpoints.values())
    total_fail = sum(stats.total_fail for stats in endpoints.values())
    uptime = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    header_text = (
        f"Tiempo activo: {uptime} | Solicitudes: {total_requests} "
        f"(OK: {total_success} / ERR: {total_fail}) | Endpoints mon.: {len(endpoints)}"
    )
    return Panel(Text(header_text, style="bold cyan"), title="Telecable Terminal Monitor", padding=(0, 1))


def render_main_table(endpoints: Dict[str, EndpointStats]) -> Table:
    table = Table(
        title="Estado de Endpoints",
        box=box.SIMPLE_HEAVY,
        header_style="bold white",
        expand=True,
    )
    table.add_column("Nombre", style="bold")
    table.add_column("URL", overflow="fold")
    table.add_column("Último", style="bold")
    table.add_column("Latencia ms")
    table.add_column("Promedio 1m")
    table.add_column("p95 1m")
    table.add_column("Éxito 1m")
    table.add_column("Req/s 1m")

    for name, stats in endpoints.items():
        window = stats.window_stats()

        if stats.last_status_code is None:
            last_status = Text("sin datos", style="yellow")
        elif stats.last_status_code == 0:
            last_status = Text("error red", style="red")
        elif stats.last_status_code < 400:
            last_status = Text(f"{stats.last_status_code}", style="green")
        else:
            last_status = Text(f"{stats.last_status_code}", style="red")

        last_latency = f"{stats.last_latency_ms:.1f}" if stats.last_latency_ms is not None else "—"
        avg_latency = f"{window['avg_ms']:.1f}" if window["avg_ms"] is not None else "—"
        p95_latency = f"{window['p95_ms']:.1f}" if window["p95_ms"] is not None else "—"
        success_rate = f"{window['success_rate']:.1f}%" if window["success_rate"] is not None else "—"
        rps = f"{window['rps']:.2f}" if window["rps"] is not None else "—"

        table.add_row(
            name,
            stats.config.url,
            last_status,
            last_latency,
            avg_latency,
            p95_latency,
            success_rate,
            rps,
        )
    return table


def render_events(events: Deque[Text]) -> Panel:
    if not events:
        content = Text("Esperando primeras muestras...", style="italic")
    else:
        content = Group(*events)
    return Panel(content, title="Eventos recientes", box=box.SIMPLE_HEAVY)


def render_health_summary(endpoints: Dict[str, EndpointStats]) -> Panel:
    lines: List[Text] = []
    for name, stats in endpoints.items():
        window = stats.window_stats()
        if window["success_rate"] is None:
            style = "yellow"
            status = "sin datos"
        elif window["success_rate"] >= 99:
            style = "green"
            status = f"{window['success_rate']:.1f}% excelente"
        elif window["success_rate"] >= 95:
            style = "yellow"
            status = f"{window['success_rate']:.1f}% aceptable"
        else:
            style = "red"
            status = f"{window['success_rate']:.1f}% crítico"
        text = Text(f"{name:<15} {status}", style=style)
        lines.append(text)
    content = Group(*lines) if lines else Text("sin endpoints configurados", style="italic")
    return Panel(content, title="Salud (último minuto)", box=box.SIMPLE_HEAVY)


def create_layout() -> Layout:
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=2),
        Layout(name="footer", size=10),
    )
    layout["footer"].split_row(
        Layout(name="health"),
        Layout(name="events"),
    )
    return layout


def dashboard_loop(
    configs: List[EndpointConfig],
    interval: float,
    history: float,
    use_screen: bool,
) -> None:
    console = Console()
    layout = create_layout()
    stats: Dict[str, EndpointStats] = {
        config.name: EndpointStats(config=config, history_seconds=history) for config in configs
    }
    events: Deque[Text] = deque(maxlen=8)
    start_time = time.time()

    def push_event(message: str, style: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        events.appendleft(Text(f"[{timestamp}] {message}", style=style))

    live = Live(layout, refresh_per_second=4, screen=use_screen, console=console)
    with live:
        try:
            while True:
                loop_start = time.perf_counter()
                for name, stat in stats.items():
                    ok, latency_ms, status_code, error = run_probe(stat.config)
                    stat.record(ok, latency_ms, status_code, error)
                    if ok:
                        push_event(f"{name} OK {latency_ms:.1f} ms", "green")
                    else:
                        err_msg = error or "sin detalle"
                        push_event(f"{name} fallo {err_msg}", "bold red")

                uptime = time.time() - start_time
                layout["header"].update(render_header(uptime, stats))
                layout["body"].update(render_main_table(stats))
                layout["footer"]["health"].update(render_health_summary(stats))
                layout["footer"]["events"].update(render_events(events))

                elapsed = time.perf_counter() - loop_start
                sleep_for = max(0.0, interval - elapsed)
                time.sleep(sleep_for)
        except KeyboardInterrupt:
            push_event("Interrupción manual detectada. Cerrando...", "yellow")
            layout["footer"]["events"].update(render_events(events))
            time.sleep(0.5)


def main() -> None:
    args = parse_args()
    configs = build_endpoints(args)
    try:
        dashboard_loop(
            configs=configs,
            interval=max(0.5, args.interval),
            history=max(5.0, args.history),
            use_screen=not args.no_screen,
        )
    except requests.exceptions.RequestException as exc:
        raise SystemExit(f"Error de red no controlado: {exc}") from exc


if __name__ == "__main__":
    main()
