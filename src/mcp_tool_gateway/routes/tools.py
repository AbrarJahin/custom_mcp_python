from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..tools.registry import list_tool_specs, get_tool

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
def list_tools() -> list[dict]:
    """List registered MCP tools (name + description)."""
    return [{"name": s.name, "description": s.description} for s in list_tool_specs()]


@router.get("/{tool_name}")
def tool_details(tool_name: str) -> dict:
    """Return details for a specific tool by name."""
    tool = get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    spec = tool.spec
    return {"name": spec.name, "description": spec.description}
