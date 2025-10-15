from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


RouterPowerState = Literal["on", "off"]


class RouterCreate(BaseModel):
    cliente_id: int = Field(..., gt=0)
    nombre: Optional[str] = None


class RouterAction(BaseModel):
    action: Literal["on", "off", "reboot"]


class RouterLogEntry(BaseModel):
    timestamp: datetime
    message: str


class RouterInfo(BaseModel):
    router_id: str
    cliente_id: Optional[int]
    state: RouterPowerState
    ip: str
    created_at: datetime
    last_state_change: datetime
    uptime: float = 0
    logs: list[RouterLogEntry] = Field(default_factory=list)


class RouterEvent(BaseModel):
    event: Literal["state", "keepalive"]
    router_id: str
    state: RouterPowerState
    uptime: float
    timestamp: datetime
    ip: str
