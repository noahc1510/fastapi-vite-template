from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.schema import AIOSTaskBootstrapRequest, AIOSTaskBootstrapResponse
from app.service.aios_task import (
    create_aios_task,
    exchange_pat_to_aios_access_token,
    kickoff_aios_chat,
)

from app.config import config as cfg

router = APIRouter(prefix="/aios", tags=["aios"])


def _extract_pat_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        if token:
            return token
    pat_header = request.headers.get("x-pat-token")
    if pat_header:
        return pat_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少 PAT 令牌，请在 Authorization 或 X-PAT-TOKEN 中提供",
    )


@router.post(
    "/tasks/bootstrap",
    response_model=AIOSTaskBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_aios_task(
    payload: AIOSTaskBootstrapRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> AIOSTaskBootstrapResponse:
    """
    创建 AIOS 任务并异步发送首条聊天消息。
    """
    pat_token = _extract_pat_token(request)
    access_token = await exchange_pat_to_aios_access_token(pat_token, resources=[cfg.AIOS_API_ENDPOINT])
    task = await create_aios_task(
        agent_id=payload.agent_id,
        access_token=access_token,
        task_name=payload.task_name,
    )
    task_id = task.get("id")
    task_name = task.get("name") or ""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AIOS 创建任务未返回任务 ID"
        )

    background_tasks.add_task(
        kickoff_aios_chat,
        task_id=task_id,
        agent_id=payload.agent_id,
        initial_message=payload.initial_message,
        access_token=access_token,
    )

    return AIOSTaskBootstrapResponse(task_id=task_id, task_name=task_name)
