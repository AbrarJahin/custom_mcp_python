from fastapi import APIRouter
from mcp_tool_gateway.config import settings

router = APIRouter()

@router.get("/health")
def health():
    return {
        "ok": True,
        "auth_enabled": settings.mcp_enable_auth,
    }
