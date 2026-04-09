from fastapi import APIRouter

from .tg_chat.handlers import router as tg_chat_router
from .links.handlers import router as links_router

__all__ = ("router",)

router = APIRouter()
router.include_router(tg_chat_router)
router.include_router(links_router)
