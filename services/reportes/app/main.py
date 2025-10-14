import os
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "reportes")
api_keys = {k.strip() for k in os.getenv("API_KEYS", "demo-key").split(",") if k.strip()}
catalogo_url = os.getenv("CATALOGO_URL", "http://catalogo:8001")

app = FastAPI(title="Servicio Reportes & API Pública", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


def _check_api_key(request: Request):
    key = request.headers.get("X-API-Key")
    if not key or key not in api_keys:
        raise HTTPException(status_code=401, detail="api key requerida")


@app.get("/public/catalogo/planes")
async def public_planes(request: Request, zona: Optional[str] = None, velocidad: Optional[int] = None):
    _check_api_key(request)
    params = {}
    if zona:
        params["zona"] = zona
    if velocidad:
        params["velocidad"] = str(velocidad)
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{catalogo_url.rstrip('/')}/catalogo/planes", params=params)
        r.raise_for_status()
        return r.json()


rate_counts = {}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # simple token-bucket per-ip per-minute
    ident = request.client.host if request.client else "anon"
    now_min = datetime.utcnow().strftime("%Y%m%d%H%M")
    key = f"{ident}:{now_min}"
    cnt = rate_counts.get(key, 0)
    if cnt > 200:  # 200 req/min per origen
        raise HTTPException(status_code=429, detail="rate limit")
    rate_counts[key] = cnt + 1
    return await call_next(request)


@app.get("/bi/kpis")
async def bi_kpis(mes: Optional[str] = None):
    # demo aggregation
    mes = mes or datetime.utcnow().strftime("%Y-%m")
    return {
        "mes": mes,
        "zona": {
            "NORTE": {"altas": 20, "bajas": 1, "morosidad": 0.05, "reconexiones": 3, "tickets": 5, "pagos": 18},
            "SUR": {"altas": 15, "bajas": 2, "morosidad": 0.08, "reconexiones": 4, "tickets": 6, "pagos": 14},
        },
    }


@app.post("/bi/churn/backtest")
def churn_backtest():
    # simple fake backtest to generate evidence files
    out_dir = "/app/exports/bi"
    os.makedirs(out_dir, exist_ok=True)
    # backtest.csv
    lines = ["mes,zona,real,pred,abs_err"]
    data = [
        ("2025-07","NORTE",0.06,0.055),
        ("2025-08","NORTE",0.065,0.06),
        ("2025-09","NORTE",0.062,0.061),
        ("2025-07","SUR",0.08,0.075),
        ("2025-08","SUR",0.082,0.081),
        ("2025-09","SUR",0.079,0.078),
    ]
    mape_sum = 0.0
    for mes,z,real,pred in data:
        abs_err = abs(real - pred)
        mape_sum += abs_err / real
        lines.append(f"{mes},{z},{real},{pred},{abs_err}")
    mape = round((mape_sum / len(data)) * 100.0, 2)
    with open(f"{out_dir}/backtest.csv","w",encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(f"{out_dir}/mape.json","w",encoding="utf-8") as f:
        json.dump({"MAPE": mape}, f)
    return {"ok": True, "out": "/exports/bi", "MAPE": mape}


Instrumentator().instrument(app).expose(app)

