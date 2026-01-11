from mcp_tool_gateway.mcp_instance import mcp
from mcp_tool_gateway.tools import register_all_tools

register_all_tools()

__all__ = ["mcp"]
