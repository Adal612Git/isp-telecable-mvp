import asyncio
import json
import os
from typing import Any

from aiokafka import AIOKafkaProducer


class EventBus:
    def __init__(self) -> None:
        self.broker = os.getenv("KAFKA_BROKER")
        self.enabled = bool(self.broker)
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        if self.enabled and self._producer is None:
            try:
                self._producer = AIOKafkaProducer(bootstrap_servers=self.broker)
                await self._producer.start()
            except Exception:
                # fallback to file-only mode
                self.enabled = False
                self._producer = None

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def publish(self, topic: str, payload: dict[str, Any]):
        body = json.dumps(payload).encode("utf-8")
        if self._producer:
            await self._producer.send_and_wait(topic, body)
        # Always also mirror to file-based log for tests/evidence
        try:
            os.makedirs("/app_events", exist_ok=True)
            with open("/app_events/events.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"topic": topic, "payload": payload}) + "\n")
        except Exception:
            pass

event_bus = EventBus()
