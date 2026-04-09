from fastapi import APIRouter

from . import ping, updates

__all__ = ("router",)

router = APIRouter()
router.include_router(ping.router, tags=["ping"])
router.include_router(updates.router, tags=["updates"])
