from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import config
from app.schema import (
    PATCreateRequest,
    PATCreateResponse,
    PATExchangeRequest,
    PATExchangeResponse,
    PATResponse,
)
from app.service.logto import introspect_access_token
from app.service.logto_pat import (
    logto_pat_create,
    logto_pat_delete,
    logto_pat_exchange,
    logto_pat_list,
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
            id=str(pat.get("id") or pat.get("patId")),
            name=pat.get("name", ""),
            description=pat.get("description"),
            scopes=pat.get("scopes") or [],
            expires_at=pat.get("expiresAt"),
            last_used_at=pat.get("lastUsedAt"),
            logto_pat_id=str(pat.get("id") or pat.get("patId")),
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
        description=payload.description,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        resource=resource,
        user_id=claims.get("sub"),
    )
    token_value = created.get("value")
    return PATCreateResponse(
        id=str(created.get("id") or created.get("patId")),
        name=created.get("name", payload.name),
        description=created.get("description"),
        scopes=created.get("scopes") or payload.scopes,
        expires_at=created.get("expiresAt") or payload.expires_at,
        last_used_at=created.get("lastUsedAt"),
        logto_pat_id=str(created.get("id") or created.get("patId")),
        is_revoked=created.get("isRevoked", False),
        created_at=created.get("createdAt") or datetime.now(timezone.utc),
        token=token_value,
    )


@router.delete("/{pat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pat(
        pat_id: str,
        auth: tuple[dict, str] = Depends(ensure_logto_user),
        # access_token: str = Depends(get_access_token)
    ):
    claims, token = auth
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法从令牌中获取用户信息",
        )

    await logto_pat_delete(pat_id, user_id=user_id, access_token = token)
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
    pat_value = _extract_pat_token(request, payload)
    resource = payload.resource if payload else config.TARGET_SERVICE_BASE_URL
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
