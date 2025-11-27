from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, status
from nanoid import generate
from sqlalchemy.orm import Session

from app.config import config
from app.db.model import PersonalAccessToken, User
from app.service.logto import create_logto_pat_via_api


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_scopes(scopes: list[str]) -> list[str]:
    return sorted({scope.strip() for scope in scopes if scope.strip()})


def _serialize_scopes(scopes: list[str]) -> str:
    return ",".join(_normalize_scopes(scopes))


def _parse_scopes(scopes: str | None) -> list[str]:
    return [scope for scope in (scopes or "").split(",") if scope]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_pat(
    db: Session,
    *,
    user: User,
    name: str,
    description: str | None,
    scopes: list[str],
    expires_at: datetime | None,
) -> tuple[str, PersonalAccessToken]:
    token_value = f"{config.PAT_TOKEN_PREFIX}_{generate(size=config.PAT_TOKEN_SIZE)}"
    token_prefix = token_value[:12]
    token_hash = _hash_token(token_value)
    normalized_scopes = _normalize_scopes(scopes)

    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    logto_pat_id = None
    # Best-effort create PAT via Logto Management API, ignore failures.
    logto_response = await create_logto_pat_via_api(name, normalized_scopes, expires_at)
    if logto_response and isinstance(logto_response, dict):
        logto_pat_id = str(logto_response.get("id") or logto_response.get("patId"))

    pat = PersonalAccessToken(
        user_id=user.id,
        name=name,
        description=description,
        token_prefix=token_prefix,
        token_hash=token_hash,
        scopes=_serialize_scopes(normalized_scopes),
        expires_at=expires_at,
        logto_pat_id=logto_pat_id,
    )

    db.add(pat)
    db.commit()
    db.refresh(pat)
    return token_value, pat


def list_pats(db: Session, user: User) -> list[PersonalAccessToken]:
    return (
        db.query(PersonalAccessToken)
        .filter(
            PersonalAccessToken.user_id == user.id,
            PersonalAccessToken.is_revoked.is_(False),
        )
        .order_by(PersonalAccessToken.created_at.desc())
        .all()
    )


def revoke_pat(db: Session, pat_id: int, user: User) -> None:
    pat = (
        db.query(PersonalAccessToken)
        .filter(
            PersonalAccessToken.id == pat_id,
            PersonalAccessToken.user_id == user.id,
            PersonalAccessToken.is_revoked.is_(False),
        )
        .first()
    )
    if not pat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PAT 不存在")
    pat.is_revoked = True
    db.add(pat)
    db.commit()


def verify_pat(db: Session, token_value: str) -> PersonalAccessToken:
    if not token_value or not token_value.startswith(f"{config.PAT_TOKEN_PREFIX}_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少或无效的 PAT"
        )
    token_hash = _hash_token(token_value)
    token_prefix = token_value[:12]

    pat = (
        db.query(PersonalAccessToken)
        .filter(
            PersonalAccessToken.token_prefix == token_prefix,
            PersonalAccessToken.is_revoked.is_(False),
        )
        .first()
    )
    if not pat or pat.token_hash != token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="PAT 不存在或已失效"
        )
    if pat.user and getattr(pat.user, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已被禁用"
        )
    if pat.expires_at and pat.expires_at < _now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="PAT 已过期"
        )

    pat.last_used_at = _now()
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat


def pat_to_schema(pat: PersonalAccessToken) -> dict:
    return {
        "id": pat.id,
        "name": pat.name,
        "description": pat.description,
        "scopes": _parse_scopes(pat.scopes),
        "expires_at": pat.expires_at,
        "last_used_at": pat.last_used_at,
        "logto_pat_id": pat.logto_pat_id,
        "is_revoked": pat.is_revoked,
        "created_at": pat.created_at,
    }


def mint_gateway_token(pat: PersonalAccessToken, user: User) -> tuple[str, int]:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="缺少用户信息，无法签发访问令牌"
        )
    expires_in = config.GATEWAY_JWT_EXPIRES_SECONDS
    now_seconds = int(time.time())
    payload = {
        "sub": user.uid,
        "pat_id": pat.id,
        "scopes": _parse_scopes(pat.scopes),
        "iat": now_seconds,
        "iss": config.GATEWAY_JWT_ISSUER,
        "exp": now_seconds + expires_in,
    }
    token = jwt.encode(payload, config.GATEWAY_JWT_SECRET, algorithm="HS256")
    return token, expires_in


def decode_gateway_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            config.GATEWAY_JWT_SECRET,
            algorithms=["HS256"],
            issuer=config.GATEWAY_JWT_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="访问令牌无效"
        ) from exc
