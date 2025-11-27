from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException, status
from loguru import logger

from app.config import config


async def introspect_access_token(token: str) -> dict[str, Any]:
    """
    Validate a Logto access token via the introspection endpoint.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少访问令牌"
        )

    payload = {
        "token": token,
        "client_id": config.LOGTO_CLIENT_ID,
        "client_secret": config.LOGTO_CLIENT_SECRET,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(config.LOGTO_INTROSPECTION_ENDPOINT, data=payload)
    except httpx.HTTPError as exc:
        logger.exception("Logto introspection failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Logto introspection error: {exc}",
        ) from exc

    if response.status_code >= 400:
        logger.error("Logto introspection error %s: %s", response.status_code, response.text)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法校验访问令牌",
        )

    data = response.json()
    if not data.get("active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌已失效"
        )
    return data


async def create_logto_pat_via_api(
    name: str, scopes: list[str], expires_at: datetime | None
) -> dict[str, Any] | None:
    """
    Optionally call the Logto Management API to mint a PAT in Logto itself.

    If LOGTO_MANAGEMENT_API_BASE or LOGTO_MANAGEMENT_API_TOKEN is not configured,
    this returns None and the backend will fall back to issuing a local PAT.
    """
    if not config.LOGTO_MANAGEMENT_API_BASE or not config.LOGTO_MANAGEMENT_API_TOKEN:
        return None

    endpoint = config.LOGTO_MANAGEMENT_API_BASE.rstrip("/") + "/personal-access-tokens"
    payload: dict[str, Any] = {"name": name, "scopes": scopes}
    if expires_at:
        payload["expiresAt"] = expires_at.isoformat()

    headers = {"Authorization": f"Bearer {config.LOGTO_MANAGEMENT_API_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("Failed to talk to Logto PAT API: %s", exc)
        return None

    if resp.status_code >= 300:
        logger.warning(
            "Logto PAT API returned %s: %s", resp.status_code, resp.text
        )
        return None

    return resp.json()
