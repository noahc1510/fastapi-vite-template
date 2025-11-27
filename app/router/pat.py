from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schema import (
    PATCreateRequest,
    PATCreateResponse,
    PATExchangeRequest,
    PATExchangeResponse,
    PATResponse,
)
from app.service.logto import introspect_access_token
from app.service.pat import create_pat, list_pats, mint_gateway_token, pat_to_schema, revoke_pat, verify_pat
from app.service.user import upsert_user_from_claims

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


async def get_current_user(
    db: Session = Depends(get_db), access_token: str = Depends(get_access_token)
):
    claims = await introspect_access_token(access_token)
    try:
        return upsert_user_from_claims(db, claims)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("", response_model=list[PATResponse])
async def list_my_pats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    pats = list_pats(db, current_user)
    return [pat_to_schema(p) for p in pats]


@router.post("", response_model=PATCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_my_pat(
    payload: PATCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_value, pat = await create_pat(
        db,
        user=current_user,
        name=payload.name,
        description=payload.description,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    data = pat_to_schema(pat)
    return PATCreateResponse(**data, token=token_value)


@router.delete("/{pat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pat(pat_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_pat(db, pat_id, current_user)
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
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 PAT"
    )


@router.post("/exchange", response_model=PATExchangeResponse)
async def exchange_pat(
    request: Request,
    payload: PATExchangeRequest | None = None,
    db: Session = Depends(get_db),
):
    pat_value = _extract_pat_token(request, payload)
    pat = verify_pat(db, pat_value)
    user = pat.user
    token, expires_in = mint_gateway_token(pat, user)
    return PATExchangeResponse(
        access_token=token,
        expires_in=expires_in,
        issued_at=int(
            (pat.updated_at or pat.created_at or datetime.now(timezone.utc)).timestamp()
        ),
        pat_id=pat.id,
    )
from datetime import datetime, timezone
