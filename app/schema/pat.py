from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PATCreateRequest(BaseModel):
    name: str = Field(..., description="友好名称，帮助识别令牌用途")
    expires_at: datetime | None = Field(
        default=None, description="到期时间（UTC）。为空则长期有效"
    )


class PATResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    expires_at: datetime | str | None
    logto_pat_id: str | None
    is_revoked: bool
    created_at: datetime | str


class PATCreateResponse(PATResponse):
    token: str


class PATExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    issued_at: int
    pat_id: str


class PATExchangeRequest(BaseModel):
    token: str | None = Field(
        default=None, description="待兑换的 PAT。为空时可从 Authorization 或 X-PAT-TOKEN 头读取"
    )
    resource: str | None = Field(
        default=None, description="目标 resource/audience，不填则使用后端配置的 TARGET_SERVICE_BASE_URL"
    )
