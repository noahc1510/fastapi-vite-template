from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status
from loguru import logger

from app.config import config
from app.schema.aios_token_exchange import (
    AIOSTokenExchangeData,
    AIOSTokenExchangeRequest,
    AIOSTokenExchangeResponse,
)


async def exchange_token_with_aios(
    request: AIOSTokenExchangeRequest,
    authorization_token: str | None = None,
) -> AIOSTokenExchangeResponse:
    """
    通过 AIOS API 进行 token exchange。
    
    Args:
        request: Token exchange 请求数据
        authorization_token: 可选的授权令牌，用于请求头
        
    Returns:
        AIOS token exchange 响应
        
    Raises:
        HTTPException: 当请求失败时
    """
    if not config.AIOS_API_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 AIOS API 端点",
        )

    # 构建请求 URL
    exchange_endpoint = config.AIOS_API_ENDPOINT.rstrip("/") + "/auth/token-exchange"
    
    # 准备请求头
    headers = {
        "Content-Type": "application/json",
    }
    
    # 如果提供了授权令牌，添加到请求头
    if authorization_token:
        headers["Authorization"] = f"Bearer {authorization_token}"
    
    try:
        # 验证请求对象类型
        if not isinstance(request, AIOSTokenExchangeRequest):
            raise ValueError(f"Invalid request type: expected AIOSTokenExchangeRequest, got {type(request)}")
        
        # 序列化请求数据
        request_data = request.model_dump()
        logger.debug(f"AIOS token exchange request data: {request_data}")
        
        # 发送请求到 AIOS API
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                exchange_endpoint,
                json=request_data,
                headers=headers,
            )
        
        # 检查响应状态
        if response.status_code >= 400:
            error_detail = f"AIOS token exchange 失败: {response.status_code}"
            error_context = ""
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    if error_data.get("message"):
                        error_detail = f"AIOS token exchange 失败: {error_data['message']}"
                    if error_data.get("error_description"):
                        error_context = f" ({error_data['error_description']})"
                    elif error_data.get("error"):
                        error_context = f" (错误码: {error_data['error']})"
            except Exception:
                error_detail = f"AIOS token exchange 失败: {response.text}"
            
            full_error = f"{error_detail}{error_context}"
            logger.error(f"AIOS token exchange 失败: {full_error}")
            logger.error(f"AIOS 请求数据: {request_data}")
            logger.error(f"AIOS 响应状态: {response.status_code}")
            logger.error(f"AIOS 响应内容: {response.text}")
            
            raise HTTPException(
                status_code=response.status_code,
                detail=full_error,
            )
        
        # 解析响应数据
        response_data = response.json()
        
        # 验证响应格式
        if not isinstance(response_data, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AIOS API 返回格式错误",
            )
        
        # 创建响应对象
        return AIOSTokenExchangeResponse(
            ok=response_data.get("ok", False),
            data=AIOSTokenExchangeData(
                access_token=response_data["data"]["accessToken"],
                token_type=response_data["data"]["tokenType"],
                expires_in=response_data["data"]["expiresIn"],
                scope=response_data["data"]["scope"],
                # issued_token_type=response_data["data"]["issuedTokenType"],
            ) if response_data.get("data") else None,
            message=response_data.get("message"),
        )
        
    except httpx.TimeoutException:
        logger.error("AIOS token exchange 请求超时")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AIOS token exchange 请求超时",
        )
    except httpx.ConnectError:
        logger.error("无法连接到 AIOS API")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="无法连接到 AIOS API",
        )
    except KeyError as e:
        logger.error(f"AIOS API 响应缺少必要字段: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AIOS API 响应格式错误: 缺少字段 {e}",
        )
    except Exception as e:
        logger.error(f"AIOS token exchange 发生未知错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AIOS token exchange 发生错误: {str(e)}",
        )


def create_default_aios_token_exchange_request(
    resources: list[str] | None = None,
    scopes: list[str] | None = None,
    context_pattern: str = "^(.*)$",
) -> AIOSTokenExchangeRequest:
    """
    创建默认的 AIOS token exchange 请求。
    
    Args:
        resources: 资源列表，默认为空列表
        scopes: 作用域列表，默认为空列表
        context_pattern: 上下文模式，默认为 "^(.*)$"
        
    Returns:
        默认的 AIOS token exchange 请求对象
    """
    return AIOSTokenExchangeRequest(
        resources=resources or [""],
        context={context_pattern: None},
        scopes=scopes or [""],
    )