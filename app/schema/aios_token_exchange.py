from pydantic import BaseModel, Field


class AIOSTokenExchangeRequest(BaseModel):
    resources: list[str] = Field(
        default_factory=list,
        description="资源列表，默认为空列表"
    )
    context: dict[str, str | None] = Field(
        default_factory=dict,
        description="上下文信息，键值对格式，值可以为null"
    )
    scopes: list[str] = Field(
        default_factory=list,
        description="作用域列表，默认为空列表"
    )


class AIOSTokenExchangeData(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(..., description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    scope: str = Field(..., description="作用域")
    # issued_token_type: str = Field(..., description="发行的令牌类型")


class AIOSTokenExchangeResponse(BaseModel):
    ok: bool = Field(..., description="请求是否成功")
    data: AIOSTokenExchangeData | None = Field(
        default=None, description="返回的数据"
    )
    message: str | None = Field(default=None, description="消息说明")