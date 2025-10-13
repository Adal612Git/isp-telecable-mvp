#!/usr/bin/env python3
"""Simulador de métricas Prometheus con datos aleatorios para prueba de tableros.

Este servicio expone un endpoint HTTP compatible con Prometheus que actualiza
continuamente varias métricas de telecomunicaciones con valores aleatorios.
Útil para poblar dashboards de Grafana con tráfico simulado.
"""

from __future__ import annotations

import argparse
import logging
import random
import threading
import time
from typing import Iterable

from prometheus_client import Counter, Gauge, Histogram, start_http_server

LOG = logging.getLogger("telecable.metrics.simulator")


def parse_args() -> argparse.Namespace:
    """Define parámetros CLI para el simulador."""
    parser = argparse.ArgumentParser(
        description=(
            "Expone métricas sintéticas con valores aleatorios para alimentar "
            "Prometheus y Grafana."
        )
    )
    parser.add_argument(
        "--addr",
        default="0.0.0.0",
        help="Dirección de escucha del servidor HTTP (default: %(default)s).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9108,
        help="Puerto de escucha del servidor HTTP (default: %(default)s).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Segundos entre iteraciones de simulación (default: %(default)s).",
    )
    parser.add_argument(
        "--services",
        nargs="+",
        default=["internet", "video", "voip"],
        help="Lista de servicios simulados (default: %(default)s).",
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        default=["norte", "centro", "sur"],
        help="Lista de regiones simuladas (default: %(default)s).",
    )
    parser.add_argument(
        "--max-subscribers",
        type=int,
        default=5000,
        help="Cantidad máxima de suscriptores activos por región.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Semilla para el generador aleatorio (opcional, útil para reproducibilidad).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Nivel de logging del simulador (default: %(default)s).",
    )
    return parser.parse_args()


class MetricSimulator:
    """Genera y publica métricas sintéticas."""

    def __init__(
        self,
        services: Iterable[str],
        regions: Iterable[str],
        max_subscribers: int,
        interval: float,
    ) -> None:
        self.services = list(services)
        self.regions = list(regions)
        self.max_subscribers = max_subscribers
        self.interval = interval
        self._stop_event = threading.Event()
        self._start_time = time.time()

        # Métricas publicadas
        self._latency_seconds = Histogram(
            "telecable_request_latency_seconds",
            "Latencia percibida de solicitudes por servicio y región.",
            ["service", "region"],
        )
        self._throughput = Counter(
            "telecable_requests_total",
            "Total de solicitudes procesadas por servicio y región.",
            ["service", "region"],
        )
        self._errors = Counter(
            "telecable_request_errors_total",
            "Total de errores generados por servicio y región.",
            ["service", "region"],
        )
        self._bandwidth = Gauge(
            "telecable_bandwidth_mbps",
            "Uso de ancho de banda agregado por región (Mbps).",
            ["region"],
        )
        self._active_subscribers = Gauge(
            "telecable_active_subscribers",
            "Suscriptores activos por región.",
            ["region"],
        )
        self._uptime = Gauge(
            "telecable_service_uptime_seconds",
            "Tiempo de actividad acumulado por servicio.",
            ["service"],
        )
        self._iteration = Counter(
            "telecable_simulation_iterations_total",
            "Iteraciones ejecutadas por el simulador.",
        )

    def stop(self) -> None:
        """Solicita detener el bucle de simulación."""
        self._stop_event.set()

    def run(self) -> None:
        """Ejecuta el bucle continuo de simulación hasta recibir Ctrl+C."""
        LOG.info("Iniciando simulador con %s servicios y %s regiones.", len(self.services), len(self.regions))
        try:
            while not self._stop_event.is_set():
                iteration_start = time.perf_counter()
                self._simulate_iteration()
                elapsed = time.perf_counter() - iteration_start
                sleep_time = max(0.0, self.interval - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            LOG.info("Interrupción recibida, cerrando simulador...")
        finally:
            self.stop()
            LOG.info("Simulador detenido.")

    def _simulate_iteration(self) -> None:
        """Genera un conjunto de muestras para todas las combinaciones servicio/región."""
        self._iteration.inc()
        now = time.time()

        for service in self.services:
            uptime = now - self._start_time
            self._uptime.labels(service=service).set(uptime)

            for region in self.regions:
                base_load = random.uniform(500, 1500)
                seasonal_amp = random.uniform(0.8, 1.2)
                jitter = random.uniform(0.7, 1.3)
                requests = max(1, int(base_load * seasonal_amp * jitter))

                latency = max(0.02, random.gauss(0.25, 0.05))
                if random.random() < 0.15:
                    latency *= random.uniform(1.5, 3.0)  # picos ocasionales

                error_chance = random.uniform(0.005, 0.05)
                errors = int(requests * error_chance if random.random() < 0.5 else requests * error_chance * 0.1)
                errors = max(0, int(errors))

                bandwidth = requests * random.uniform(0.5, 1.5) / 10.0

                self._latency_seconds.labels(service=service, region=region).observe(latency)
                self._throughput.labels(service=service, region=region).inc(requests)
                if errors:
                    self._errors.labels(service=service, region=region).inc(errors)
                self._bandwidth.labels(region=region).set(bandwidth)

                subscribers_base = self.max_subscribers * random.uniform(0.6, 0.95)
                fluctuation = random.uniform(-0.08, 0.08) * subscribers_base
                subscribers = max(0, subscribers_base + fluctuation)
                self._active_subscribers.labels(region=region).set(subscribers)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    if args.seed is not None:
        random.seed(args.seed)
        LOG.debug("Semilla de aleatoriedad fijada en %s", args.seed)

    LOG.info("Publicando métricas en http://%s:%s/metrics", args.addr, args.port)
    start_http_server(port=args.port, addr=args.addr)

    simulator = MetricSimulator(
        services=args.services,
        regions=args.regions,
        max_subscribers=args.max_subscribers,
        interval=args.interval,
    )
    simulator.run()


if __name__ == "__main__":
    main()
