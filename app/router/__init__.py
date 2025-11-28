from fastapi import APIRouter
from .user import router as user_router
from .pat import router as pat_router
from .gateway import router as gateway_router
from .aios_task import router as aios_task_router

api_router = APIRouter()
api_router.include_router(user_router, prefix="", tags=["user"])
api_router.include_router(pat_router, prefix="", tags=["pat"])
api_router.include_router(gateway_router, prefix="", tags=["gateway"])
api_router.include_router(aios_task_router, prefix="", tags=["aios"])
