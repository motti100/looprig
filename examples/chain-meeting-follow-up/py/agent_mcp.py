"""chain-meeting-follow-up as an MCP server
Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain

Exported by LoopRig. It offers this agent's tools to any MCP client (Claude Desktop, Claude Code, Cursor and others),
plus ask_agent, which runs the whole agent from agent.py.

  pip install mcp
  python agent_mcp.py                       # speaks MCP over stdio

Claude Code:     claude mcp add chain-meeting-follow-up -- python /full/path/to/agent_mcp.py
Claude Desktop:  add {"mcpServers": {"chain-meeting-follow-up": {"command": "python", "args": ["/full/path/to/agent_mcp.py"]}}} to its config
"""
import contextlib
import os
import sys

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x

ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"
app = Server("chain-meeting-follow-up")


# No safe tools selected.


@app.tool()
def ask_agent(task: str) -> str:
    """Give the whole chain-meeting-follow-up agent a task and return its answer. It uses your model and API key, so it costs tokens."""
    from agent import run  # imported here so the server starts without an API key

    with contextlib.redirect_stdout(sys.stderr):  # the agent prints its steps; MCP needs stdout for itself
        return str(run(task))


if __name__ == "__main__":
    app.run()
