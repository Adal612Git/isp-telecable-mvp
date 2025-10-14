import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


service_name = os.getenv("SERVICE_NAME", "whatsapp")


def setup_tracing():
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    jaeger_endpoint = os.getenv("OTEL_JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    jaeger_exporter = JaegerExporter(agent_host_name=None, collector_endpoint=jaeger_endpoint)
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(provider)


app = FastAPI(title="WhatsApp Mock", version="0.1.0")


@app.on_event("startup")
async def on_startup():
    setup_tracing()


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


@app.get("/webhook")
def verify(mode: str | None = None, hub_mode: str | None = None, hub_verify_token: str | None = None, hub_challenge: str | None = None):
    token = os.getenv("WHATSAPP_VERIFY_TOKEN", "testtoken")
    verify_token = hub_verify_token or token
    if verify_token != token:
        raise HTTPException(status_code=403, detail="Invalid token")
    return PlainTextResponse(content=hub_challenge or "ok")


@app.post("/webhook")
async def receive(request: Request):
    body = await request.json()
    return JSONResponse(content={"status": "received", "keys": list(body.keys())})


@app.post("/send-template")
async def send_template(body: dict):
    # emulation only
    return {"status": "sent", "to": body.get("to"), "template": body.get("template"), "mode": "test"}

# expose metrics at import time
Instrumentator().instrument(app).expose(app)
