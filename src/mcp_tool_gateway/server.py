from .mcp_instance import mcp
from .tools import register_all_tools

register_all_tools()

__all__ = ["mcp"]
