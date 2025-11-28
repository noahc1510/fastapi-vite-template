from pydantic import BaseModel, ConfigDict, Field


class AIOSTaskBootstrapRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: str = Field(..., alias="agentId", description="AIOS agent ID")
    initial_message: str = Field(
        ..., alias="initialMessage", description="首条用户消息内容"
    )
    task_name: str | None = Field(
        default=None,
        alias="taskName",
        description="任务名称，默认留空由 AIOS 处理",
    )


class AIOSTaskBootstrapResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., alias="taskId", description="AIOS 任务 ID")
    task_name: str = Field(..., alias="taskName", description="AIOS 任务名称")
