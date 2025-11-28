from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.config import config
from app.schema import (
    PATCreateRequest,
    PATCreateResponse,
    PATExchangeRequest,
    PATExchangeResponse,
    PATResponse,
)
from app.schema.aios_token_exchange import AIOSTokenExchangeRequest
from app.service.logto import introspect_access_token
from app.service.logto_pat import (
    logto_pat_create,
    logto_pat_delete,
    logto_pat_exchange,
    logto_pat_list,
)
from app.service.aios_token_exchange import (
    exchange_token_with_aios,
    create_default_aios_token_exchange_request,
)

router = APIRouter(prefix="/pat", tags=["personal_access_token"])

bearer_scheme = HTTPBearer(auto_error=False)


async def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少访问令牌"
        )
    return credentials.credentials


async def ensure_logto_user(
    access_token: str = Depends(get_access_token),
) -> tuple[dict, str]:
    return (await introspect_access_token(access_token), access_token)


@router.get("", response_model=list[PATResponse])
async def list_my_pats(auth: tuple[dict, str] = Depends(ensure_logto_user)):
    claims, access_token = auth
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法从令牌中获取用户信息",
        )
    # 基于管理端 token 拉取 PAT 列表（使用 M2M 或管理 token）
    pats = await logto_pat_list(claims, access_token)
    return [
        PATResponse(
            id=str(pat.get("name") or pat.get("id") or pat.get("patId") or ""),
            name=pat.get("name", ""),
            description=pat.get("description"),
            expires_at=pat.get("expiresAt"),
            logto_pat_id=str(pat.get("id") or pat.get("patId") or pat.get("name") or ""),
            is_revoked=pat.get("isRevoked", False),
            created_at=pat.get("createdAt"),
        )
        for pat in pats
    ]


@router.post("", response_model=PATCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_my_pat(
    payload: PATCreateRequest,
    auth: tuple[dict, str] = Depends(ensure_logto_user),
):
    claims, _ = auth
    resource = config.TARGET_SERVICE_BASE_URL or None
    created = await logto_pat_create(
        name=payload.name,
        expires_at=payload.expires_at,
        resource=resource,
        user_id=claims.get("sub"),
    )
    token_value = created.get("value")
    return PATCreateResponse(
        id=str(created.get("name") or created.get("id") or created.get("patId") or payload.name),
        name=created.get("name", payload.name),
        description=created.get("description"),
        expires_at=created.get("expiresAt") or payload.expires_at,
        logto_pat_id=str(created.get("id") or created.get("patId") or created.get("name") or payload.name),
        is_revoked=created.get("isRevoked", False),
        created_at=created.get("createdAt") or datetime.now(timezone.utc),
        token=token_value,
    )


@router.delete("/{pat_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pat(
    pat_name: str,
    auth: tuple[dict, str] = Depends(ensure_logto_user),
    # access_token: str = Depends(get_access_token)
):
    claims, _token = auth
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法从令牌中获取用户信息",
        )

    await logto_pat_delete(pat_name, user_id=user_id)
    return None


def _extract_pat_token(request: Request, payload: PATExchangeRequest | None) -> str:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        candidate = auth_header.split(" ", 1)[1]
        if candidate:
            return candidate
    pat_header = request.headers.get("x-pat-token")
    if pat_header:
        return pat_header
    if payload and payload.token:
        return payload.token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 PAT")


@router.post("/exchange", response_model=PATExchangeResponse)
async def exchange_pat(
    request: Request,
    payload: PATExchangeRequest | None = None,
):
    """
    Token Exchange 接口 - 使用 AIOS API 进行令牌交换。
    
    该接口将 PAT (Personal Access Token) 通过 AIOS API 交换为访问令牌。
    支持从 Authorization 头、X-PAT-TOKEN 头或请求体中获取 PAT。
    
    ## 请求方式
    
    1. **Authorization 头**: `Authorization: Bearer <pat_token>`
    2. **X-PAT-TOKEN 头**: `X-PAT-TOKEN: <pat_token>`
    3. **请求体**: 提供 `{"token": "<pat_token>", "resource": "<optional_resource>"}`
    
    ## 响应
    
    返回交换后的访问令牌信息：
    - `access_token`: 访问令牌
    - `token_type`: 令牌类型 (通常为 "bearer")
    - `expires_in`: 过期时间 (秒)
    - `issued_at`: 发行时间戳
    - `pat_id`: PAT ID
    """
    pat_value = _extract_pat_token(request, payload)
    resource = payload.resource if payload else config.TARGET_SERVICE_BASE_URL
    
    try:
        # 根据 AIOS API 要求创建请求，使用标准格式
        from app.schema.aios_token_exchange import AIOSTokenExchangeRequest
        
        # 创建符合 AIOS API 期望的请求
        aios_request = AIOSTokenExchangeRequest(
            resources=["http://localhost:8000"],  # 空资源列表，如原始示例所示
            # context={"^(.*)$": None},  # 如原始示例所示
            # scopes=[""],  # 空作用域列表，如原始示例所示
        )
        
        # 使用 AIOS API 进行 token exchange，将 PAT 作为授权令牌
        aios_response = await exchange_token_with_aios(
            request=aios_request,
            authorization_token=pat_value,  # 使用 PAT 作为授权令牌
        )
        
        # 将 AIOS 响应转换为 PATExchangeResponse 格式
        if aios_response.ok and aios_response.data:
            return PATExchangeResponse(
                access_token=aios_response.data.access_token,
                expires_in=aios_response.data.expires_in,
                issued_at=int(datetime.now(timezone.utc).timestamp()),
                pat_id=pat_value[:16] if pat_value else "",  # 使用 PAT 的前16位作为 ID
                token_type=aios_response.data.token_type,
            )
        else:
            # AIOS 返回错误
            error_msg = aios_response.message or "AIOS token exchange 失败"
            logger.warning(f"AIOS token exchange 返回错误: {error_msg}")
            
            # 对于特定的 AIOS 错误，我们也可以选择回退到 Logto
            if "invalid_target" in error_msg or "resource indicator" in error_msg:
                logger.info("AIOS 报告资源指示符错误，尝试直接回退到 Logto PAT exchange")
                # 直接抛出异常以触发回退逻辑
                raise ValueError(f"AIOS 资源错误: {error_msg}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
            
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 处理其他异常，回退到原有的 Logto PAT exchange
        logger.warning(f"AIOS token exchange 失败，回退到 Logto PAT exchange: {e}")
        logger.exception("AIOS token exchange 异常详情:")
        try:
            exchanged = await logto_pat_exchange(pat_value, resource)
            return PATExchangeResponse(
                access_token=exchanged.get("access_token") or exchanged.get("accessToken"),
                expires_in=int(
                    exchanged.get("expires_in")
                    or exchanged.get("expiresIn")
                    or config.GATEWAY_JWT_EXPIRES_SECONDS
                ),
                issued_at=int(exchanged.get("iat") or datetime.now(timezone.utc).timestamp()),
                pat_id=str(exchanged.get("pat_id") or exchanged.get("patId") or ""),
                token_type=exchanged.get("token_type")
                or exchanged.get("tokenType")
                or "bearer",
            )
        except Exception as fallback_error:
            logger.error(f"Logto PAT exchange 也失败了: {fallback_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token exchange 失败: {str(fallback_error)}",
            )
