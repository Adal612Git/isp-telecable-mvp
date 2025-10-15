# services/orquestador/app/proxy_router.py
from fastapi import APIRouter, Request, Response
import os
import httpx

router = APIRouter()

# URL del servicio RED dentro de la red de Docker
RED_URL = os.getenv("RED_URL", "http://red:8020")


def _filter_request_headers(headers):
    keep = {}
    for k, v in headers.items():
        lk = k.lower()
        # evitar hop-by-hop headers
        if lk in (
            "host",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        ):
            continue
        keep[k] = v
    return keep


def _filter_response_headers(headers):
    out = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in ("content-encoding", "transfer-encoding", "connection"):
            continue
        out[k] = v
    return out


@router.api_route("/router/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_router(path: str, request: Request):
    """
    Proxy transparente que reenvía cualquier /router/* al servicio RED definido en RED_URL.
    Mantiene query params, body y la mayoría de headers útiles.
    """
    target = f"{RED_URL}/router/{path}"
    body = await request.body()
    headers = _filter_request_headers(dict(request.headers))

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.request(
            request.method,
            target,
            content=body if body is not None and len(body) > 0 else None,
            params=dict(request.query_params),
            headers=headers,
        )

    response_headers = _filter_response_headers(resp.headers)
    return Response(content=resp.content, status_code=resp.status_code, headers=response_headers)
