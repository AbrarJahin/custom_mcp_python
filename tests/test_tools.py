# tests/test_tools.py

from mcp_tool_gateway.tools.ping import PingTool
from mcp_tool_gateway.tools.add import AddTool
from mcp_tool_gateway.tools.web_search import WebSearchTool

def test_ping():
    t = PingTool()
    assert t.run() == "pong"

def test_add():
    t = AddTool()
    assert t.run(2, 3) == 5

def test_web_search_returns_list():
    """
    Keep this test simple. It will hit the network.
    If you want fully offline tests later, we can mock.
    """
    t = WebSearchTool()
    results = t.run_sync("openai", max_results=3)  # or t.run(...) depending on your implementation
    assert isinstance(results, list)
