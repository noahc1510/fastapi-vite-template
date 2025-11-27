from __future__ import annotations

import httpx
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


async def forward_request(
    request: Request,
    *,
    target_base: str,
    path: str,
    access_token: str | None = None,
) -> Response:
    """
    Generic forwarder used by gateway endpoints.
    """
    if not target_base:
        body_bytes = await request.body()
        return JSONResponse(
            {
                "message": "TARGET_SERVICE_BASE_URL 未配置，已返回回显数据。",
                "method": request.method,
                "path": path,
                "query": dict(request.query_params),
                "body": body_bytes.decode() if body_bytes else None,
            }
        )

    target_url = target_base.rstrip("/") + "/" + path.lstrip("/")
    # Remove hop-by-hop headers that should not be forwarded.
    excluded_headers = {
        "host",
        "content-length",
        "connection",
        "accept-encoding",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in excluded_headers
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(
                request.method,
                target_url,
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"网关访问失败: {exc}") from exc

    response_headers = {
        k: v
        for k, v in resp.headers.items()
        if k.lower() in {"content-type", "cache-control", "etag"}
    }
    return Response(
        content=resp.content, status_code=resp.status_code, headers=response_headers
    )
