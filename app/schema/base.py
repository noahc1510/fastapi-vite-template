from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class BaseRequest(BaseModel, Generic[DataT]):
    data: DataT = Field(..., description="请求数据体")


class BaseResponse(BaseModel, Generic[DataT]):
    code: str = Field(..., description="业务状态码")
    message: str | None = Field(default=None, description="状态说明")
    data: DataT | None = Field(default=None, description="返回数据体")
