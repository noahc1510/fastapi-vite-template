from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException, status
from jwt import InvalidTokenError, PyJWKClient, decode
from loguru import logger

from app.config import config

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not (config.LOGTO_JWKS_ENDPOINT or config.LOGTO_ENDPOINT):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="未配置 Logto JWKS 地址",
            )
        jwks_url = config.LOGTO_JWKS_ENDPOINT or (
            config.LOGTO_ENDPOINT.rstrip("/") + "/oidc/jwks"
        )
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


async def introspect_access_token(token: str) -> dict[str, Any]:
    """
    Validate a Logto access token locally via JWKS (JWT verification).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少访问令牌"
        )

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        decode_kwargs: dict[str, Any] = {"algorithms": ["RS256", "HS256", "ES384"]}
        if config.LOGTO_CLIENT_ID:
            decode_kwargs["audience"] = config.BASE_URL
        if config.LOGTO_ENDPOINT:
            decode_kwargs["issuer"] = config.LOGTO_ENDPOINT.rstrip("/") + '/oidc'
        claims = decode(token, signing_key.key, **decode_kwargs)
    except InvalidTokenError as exc:
        logger.error("Logto JWT 验证失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌无效或已过期",
        ) from exc
    return claims


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
