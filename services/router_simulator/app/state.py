from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from .models import RouterInfo, RouterLogEntry, RouterPowerState


@dataclass
class RouterState:
    router_id: str
    cliente_id: Optional[int]
    ip: str
    created_at: datetime
    state: RouterPowerState = "on"
    last_state_change: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_accumulated: float = 0.0
    last_power_on: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    logs: list[RouterLogEntry] = field(default_factory=list)

    def current_uptime(self) -> float:
        if self.state == "on" and self.last_power_on is not None:
            delta = datetime.now(timezone.utc) - self.last_power_on
            return self.uptime_accumulated + delta.total_seconds()
        return self.uptime_accumulated

    def snapshot(self) -> RouterInfo:
        return RouterInfo(
            router_id=self.router_id,
            cliente_id=self.cliente_id,
            state=self.state,
            ip=self.ip,
            created_at=self.created_at,
            last_state_change=self.last_state_change,
            uptime=self.current_uptime(),
            logs=list(self.logs[-20:]),
        )

    def append_log(self, message: str) -> None:
        self.logs.append(
            RouterLogEntry(
                timestamp=datetime.now(timezone.utc),
                message=message,
            )
        )
        # Keep logs manageable
        if len(self.logs) > 100:
            self.logs[:] = self.logs[-100:]

    def set_state(self, new_state: RouterPowerState) -> None:
        now = datetime.now(timezone.utc)
        if new_state == self.state:
            return
        if new_state == "off":
            # accumulate uptime before turning off
            self.uptime_accumulated = self.current_uptime()
            self.last_power_on = None
        else:
            self.last_power_on = now
        self.state = new_state
        self.last_state_change = now

    def ensure_on(self) -> None:
        if self.state != "on":
            self.set_state("on")
            self.append_log("Router encendido")

    def ensure_off(self) -> None:
        if self.state != "off":
            self.set_state("off")
            self.append_log("Router apagado")


class RouterStore:
    def __init__(self) -> None:
        self._routers: Dict[str, RouterState] = {}
        self._lock = asyncio.Lock()
        self._ip_sequence = 10

    async def create_router(self, router_id: str, cliente_id: int | None, nombre: str | None) -> RouterState:
        async with self._lock:
            ip = self._generate_ip(router_id)
            router = RouterState(
                router_id=router_id,
                cliente_id=cliente_id,
                ip=ip,
                created_at=datetime.now(timezone.utc),
            )
            router.append_log("Router creado y encendido")
            self._routers[router_id] = router
            return router

    def _generate_ip(self, router_id: str) -> str:
        digest = hashlib.sha1(router_id.encode("utf-8")).digest()
        high = (digest[0] % 254) + 1
        low = (self._ip_sequence % 254) + 1
        self._ip_sequence += 1
        return f"10.10.{high}.{low}"

    async def list(self) -> list[RouterInfo]:
        async with self._lock:
            return [router.snapshot() for router in self._routers.values()]

    async def get(self, router_id: str) -> RouterInfo:
        async with self._lock:
            router = self._routers.get(router_id)
            if not router:
                raise KeyError(router_id)
            return router.snapshot()

    async def get_state(self, router_id: str) -> RouterState:
        async with self._lock:
            router = self._routers.get(router_id)
            if not router:
                raise KeyError(router_id)
            return router

    async def set_state(self, router_id: str, state: RouterPowerState, message: str | None = None) -> RouterState:
        async with self._lock:
            router = self._routers.get(router_id)
            if not router:
                raise KeyError(router_id)
            previous = router.state
            router.set_state(state)
            if message is None:
                if state == "on":
                    message = "Encendido manual"
                else:
                    message = "Apagado manual"
            if previous != state:
                router.append_log(message)
            return router

    async def update_uptime(self, router_id: str) -> RouterInfo:
        async with self._lock:
            router = self._routers.get(router_id)
            if not router:
                raise KeyError(router_id)
            # snapshot recomputes uptime
            return router.snapshot()

    async def attach_router(self, router_id: str, cliente_id: int) -> RouterState:
        async with self._lock:
            router = self._routers.get(router_id)
            if not router:
                raise KeyError(router_id)
            router.cliente_id = cliente_id
            router.append_log(f"Asignado al cliente {cliente_id}")
            return router

    async def by_cliente(self, cliente_id: int) -> Optional[RouterInfo]:
        async with self._lock:
            for router in self._routers.values():
                if router.cliente_id == cliente_id:
                    return router.snapshot()
        return None


store = RouterStore()
