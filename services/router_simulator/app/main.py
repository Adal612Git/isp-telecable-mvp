from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import RouterAction, RouterCreate, RouterEvent
from .state import store

logger = logging.getLogger("router_simulator")
logging.basicConfig(level=logging.INFO)


def now() -> datetime:
    return datetime.now(timezone.utc)


def router_base_url() -> str:
    return os.getenv("ROUTER_SIM_BASE_URL", "http://localhost")


ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
]
for var in ("PORTAL_CLIENTE_ORIGIN", "PORTAL_TECNICO_ORIGIN", "PORTAL_VENTAS_ORIGIN"):
    if os.getenv(var):
        ALLOWED_ORIGINS.append(os.getenv(var))

app = FastAPI(title="Router Simulator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, router_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(router_id, set()).add(websocket)

    async def disconnect(self, router_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._connections.get(router_id)
            if not peers:
                return
            peers.discard(websocket)
            if not peers:
                self._connections.pop(router_id, None)

    async def broadcast(self, router_id: str) -> None:
        event = await build_event(router_id, event_type="state")
        async with self._lock:
            peers = list(self._connections.get(router_id, set()))
        for ws in peers:
            try:
                await ws.send_json(event)
            except Exception:
                await self.disconnect(router_id, ws)

    async def keepalive_loop(self, router_id: str, websocket: WebSocket) -> None:
        try:
            while True:
                await asyncio.sleep(2)
                payload = await build_event(router_id, event_type="keepalive")
                await websocket.send_json(payload)
        except WebSocketDisconnect:
            logger.info("websocket for %s disconnected", router_id)
        except Exception as exc:  # pragma: no cover
            logger.warning("websocket loop error: %s", exc)
        finally:
            await self.disconnect(router_id, websocket)


ws_manager = WebSocketManager()


async def build_event(router_id: str, event_type: str = "state") -> dict[str, Any]:
    try:
        info = await store.get(router_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    event = RouterEvent(
        event=event_type, router_id=info.router_id, state=info.state, uptime=info.uptime, timestamp=now(), ip=info.ip
    )
    payload = event.model_dump()
    payload["logs"] = [log.model_dump() for log in info.logs]
    return payload


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "time": now().isoformat()}


@app.post("/routers", status_code=201)
async def create_router(payload: RouterCreate) -> Any:
    router_id = str(uuid4())
    router = await store.create_router(router_id, payload.cliente_id, payload.nombre)
    router.append_log(f"Asignado al cliente {payload.cliente_id}")
    return router.snapshot()


@app.get("/routers")
async def list_routers() -> Any:
    routers = await store.list()
    return [router.model_dump() for router in routers]


@app.get("/routers/by-client/{cliente_id}")
async def router_by_client(cliente_id: int) -> Any:
    router = await store.by_cliente(cliente_id)
    if not router:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    return router.model_dump()


@app.get("/routers/{router_id}")
async def get_router(router_id: str) -> Any:
    info = await store.get(router_id)
    return info.model_dump()


@app.post("/routers/{router_id}/power")
async def power_router(router_id: str, payload: RouterAction) -> Any:
    action = payload.action
    if action not in {"on", "off", "reboot"}:
        raise HTTPException(status_code=400, detail="Acción inválida")

    try:
        if action == "on":
            await store.set_state(router_id, "on", message="Encendido manual desde portal")
        elif action == "off":
            await store.set_state(router_id, "off", message="Apagado manual desde portal")
        else:
            await store.set_state(router_id, "off", message="Reinicio remoto iniciado")
            await ws_manager.broadcast(router_id)
            await asyncio.sleep(1)
            await store.set_state(router_id, "on", message="Reinicio remoto completado")
    except KeyError:
        raise HTTPException(status_code=404, detail="Router no encontrado")

    await ws_manager.broadcast(router_id)
    info = await store.get(router_id)
    return info.model_dump()


@app.websocket("/ws/routers/{router_id}")
async def router_socket(websocket: WebSocket, router_id: str) -> None:
    try:
        await store.get(router_id)
    except KeyError:
        await websocket.close(code=4040)
        return

    await ws_manager.connect(router_id, websocket)
    await ws_manager.broadcast(router_id)
    await ws_manager.keepalive_loop(router_id, websocket)


@app.exception_handler(KeyError)
async def handle_key_error(_: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Router no encontrado"})
