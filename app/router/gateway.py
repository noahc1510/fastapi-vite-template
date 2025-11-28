from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import config
from app.service.gateway import forward_request
from app.service.logto import introspect_access_token

router = APIRouter(prefix="/gateway", tags=["gateway"])

bearer_scheme = HTTPBearer(auto_error=False)


async def require_gateway_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 access_token"
        )
    return await introspect_access_token(credentials.credentials)


@router.get("/ping")
async def gateway_ping(claims=Depends(require_gateway_token)):
    return {"status": "ok", "sub": claims.get("sub"), "exp": claims.get("exp")}


@router.api_route(
    "/target/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    path: str,
    request: Request,
    claims=Depends(require_gateway_token),
):
    """
    Use the minted gateway JWT to access downstream service.
    """
    access_token = request.headers.get("x-target-access-token")
    if not access_token:
        access_token = request.headers.get("authorization")

    def _strip_bearer(token: str | None) -> str | None:
        if not token:
            return None
        return token.split(" ", 1)[1] if token.lower().startswith("bearer ") else token

    access_token = _strip_bearer(access_token)
    # Default to gateway JWT for downstream call if caller didn't provide one.
    if not access_token and isinstance(claims, dict):
        access_token = _strip_bearer(request.headers.get("authorization"))

    return await forward_request(
        request,
        target_base=config.TARGET_SERVICE_BASE_URL,
        path=path,
        access_token=access_token,
    )
