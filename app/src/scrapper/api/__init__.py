from fastapi import APIRouter

from .auth.handlers import router as auth_router
from .links.handlers import router as links_router
from .tg_chat.handlers import router as tg_chat_router
from .users.handlers import router as users_router

__all__ = ("router",)

router = APIRouter()
router.include_router(auth_router)
router.include_router(tg_chat_router)
router.include_router(links_router)
router.include_router(users_router)
