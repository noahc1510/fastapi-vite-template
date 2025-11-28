from __future__ import annotations

import base64
import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import config

_token_cache: dict[str, Any] = {}


async def _fetch_management_token() -> str:
    client_id = config.LOGTO_CLIENT_ID
    client_secret = config.LOGTO_CLIENT_SECRET
    if not (client_id and client_secret):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置管理端 token，且缺少 M2M/client credentials",
        )

    # 缓存
    cached = _token_cache.get("token")
    exp = _token_cache.get("exp", 0)
    if cached and exp > time.time() + 30:
        return cached

    form = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        # "resource": config.LOGTO_ENDPOINT.rstrip("/") + '/api',
        "resource": "https://default.logto.app/api",
        "scope": "all",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(config.LOGTO_TOKEN_ENDPOINT, data=form)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"获取管理端 access_token 失败: {resp.text}",
        )
    data = resp.json()
    token = data.get("access_token") or data.get("accessToken")
    expires_in = int(data.get("expires_in") or data.get("expiresIn") or 300)
    _token_cache["token"] = token
    _token_cache["exp"] = time.time() + expires_in
    return token


async def _auth_header() -> dict[str, str]:
    token = await _fetch_management_token()
    return {"Authorization": f"Bearer {token}"}


async def logto_pat_list(claims, access_token) -> list[dict[str, Any]]:
    endpoint = (
        config.LOGTO_ENDPOINT.rstrip("/")
        + f"/api/users/{claims.get('sub')}/personal-access-tokens"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(endpoint, headers=await _auth_header())
        # resp = await client.get(endpoint, headers={"Authorization": f"Bearer {access_token}"})
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Logto PAT 列表获取失败: {resp.text}",
        )
    data = resp.json()
    return data if isinstance(data, list) else []


async def logto_pat_create(
    *,
    name: str,
    description: str | None,
    scopes: list[str],
    expires_at: datetime | None,
    resource: str | None,
    user_id: str | int,
) -> dict[str, Any]:
    endpoint = (
        config.LOGTO_ENDPOINT.rstrip("/")
        + f"/api/users/{user_id}/personal-access-tokens"
    )
    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "scopes": scopes,
    }
    if resource:
        payload["resource"] = resource
    if expires_at:
        payload["expiresAt"] = expires_at.isoformat()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(endpoint, json=payload, headers=await _auth_header())
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Logto PAT 创建失败: {resp.text}",
        )
    return resp.json()


async def logto_pat_delete(pat_id: str | int, user_id: str, access_token: str) -> None:
    endpoint = (
        config.LOGTO_ENDPOINT.rstrip("/")
        + f"/api/users/{user_id}/personal-access-tokens/{pat_id}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(endpoint, headers=await _auth_header())
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Logto PAT 删除失败: {resp.text}",
        )


async def logto_pat_exchange(pat: str, resource: str | None) -> dict[str, Any]:
    """
    通过 Logto 的 OIDC token 端点，将 PAT 兑换为 access_token。
    具体 grant_type / token_type 可能因 Logto 配置而异，如有需要可调整。
    """
    form_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": pat,
        "subject_token_type": "urn:logto:token-type:personal_access_token",
    }
    if resource:
        form_data["resource"] = resource
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            config.LOGTO_TOKEN_ENDPOINT,
            data=form_data,
            headers={
                "Authorization": f"Bearer {base64.b64encode(config.LOGTO_CLIENT_ID.encode())}:{base64.b64encode(config.LOGTO_CLIENT_SECRET.encode())}"
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Logto PAT 兑换失败: {resp.text}",
        )
    return resp.json()
