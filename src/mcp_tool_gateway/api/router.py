from __future__ import annotations

from fastapi import APIRouter

from .routes.auth import router as auth_router

router = APIRouter()
# Keep original paths (router already defines /auth/token)
router.include_router(auth_router)
