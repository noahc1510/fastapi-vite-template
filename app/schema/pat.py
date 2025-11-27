from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PATCreateRequest(BaseModel):
    name: str = Field(..., description="友好名称，帮助识别令牌用途")
    description: str | None = Field(default=None, description="可选描述")
    scopes: list[str] = Field(default_factory=list, description="允许的作用域")
    expires_at: datetime | None = Field(
        default=None, description="到期时间（UTC）。为空则长期有效"
    )


class PATResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    logto_pat_id: str | None
    is_revoked: bool
    created_at: datetime


class PATCreateResponse(PATResponse):
    token: str


class PATExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    issued_at: int
    pat_id: int


class PATExchangeRequest(BaseModel):
    token: str | None = Field(
        default=None, description="待兑换的 PAT。为空时可从 Authorization 或 X-PAT-TOKEN 头读取"
    )
