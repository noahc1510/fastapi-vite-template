from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from loguru import logger

from app.config import config
from app.schema.aios_token_exchange import AIOSTokenExchangeRequest
from app.service.aios_token_exchange import exchange_token_with_aios


def _aios_base_url() -> str:
    """
    Return the configured AIOS API base URL or raise if missing.
    """
    if not config.AIOS_API_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 AIOS_API_ENDPOINT",
        )
    return config.AIOS_API_ENDPOINT.rstrip("/")


async def create_aios_task(
    *,
    agent_id: str,
    access_token: str,
    task_name: str | None = None,
    priority: int = 10,
    task_type: int = 0,
    init_data: str | None = "",
) -> dict[str, Any]:
    """
    Call AIOS task/create to create a task using PAT for authorization.
    """
    url = _aios_base_url() + "/task/create"
    payload = {
        "name": task_name or "",
        "type": task_type,
        "priority": priority,
        "agent_requirements": json.dumps({"usingAgentId": agent_id}),
        "init_data": init_data or "",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("AIOS 创建任务请求失败: {}", exc)
        raise HTTPException(status_code=502, detail="创建任务失败，请稍后重试") from exc

    try:
        resp_data: dict[str, Any] = resp.json()
    except Exception:
        logger.error("AIOS 创建任务响应无法解析: {}", resp.text)
        raise HTTPException(status_code=502, detail="AIOS 创建任务响应格式错误")

    if resp.status_code >= 400:
        message = resp_data.get("message") or f"HTTP {resp.status_code}"
        logger.error("AIOS 创建任务返回错误: {}", message)
        raise HTTPException(status_code=resp.status_code, detail=message)

    if resp_data.get("code") != 0 or not resp_data.get("data"):
        message = resp_data.get("message") or "AIOS 创建任务失败"
        logger.error("AIOS 创建任务业务错误: {}", message)
        raise HTTPException(status_code=502, detail=message)

    return resp_data["data"]


async def kickoff_aios_chat(
    *,
    task_id: str,
    agent_id: str,
    initial_message: str,
    access_token: str,
) -> None:
    """
    Fire-and-forget initial chat/stream request; logs errors but does not raise.
    """
    url = _aios_base_url() + "/chat/stream"
    payload = {
        "taskId": task_id,
        "agentId": agent_id,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": initial_message}],
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        timeout = httpx.Timeout(connect=10.0, write=10.0, read=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    logger.warning(
                        "AIOS chat/stream 启动失败 status=%s task_id=%s: %s",
                        resp.status_code,
                        task_id,
                        resp.reason_phrase,
                    )
                    return
                # Close early; we don't need the streamed content.
                await resp.aclose()
    except httpx.HTTPError as exc:
        logger.warning(
            "AIOS chat/stream 请求异常 task_id=%s: %s", task_id, exc, exc_info=True
        )
    except Exception as exc:  # pragma: no cover - safety net
        logger.warning(
            "AIOS chat/stream 未知异常 task_id=%s: %s", task_id, exc, exc_info=True
        )


async def exchange_pat_to_aios_access_token(pat_token: str,resources=[""]) -> str:
    """
    Exchange PAT to AIOS access token (JWT) for downstream requests.
    """
    request = AIOSTokenExchangeRequest(
        resources=resources,
        scopes=[""],
        context={"^(.*)$": None},
    )
    response = await exchange_token_with_aios(request=request, authorization_token=pat_token)
    if not response.ok or not response.data or not response.data.access_token:
        message = response.message or "AIOS token exchange 失败"
        logger.error("AIOS token exchange 失败: {}", message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=message,
        )
    return response.data.access_token
