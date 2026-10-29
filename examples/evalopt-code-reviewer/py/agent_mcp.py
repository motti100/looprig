"""evalopt-code-reviewer as an MCP server
Reason: direct | Act: read_file | Observe: raw | Decide: evaluate >= 8 | Shape: single agent

Exported by LoopRig. It offers this agent's tools to any MCP client (Claude Desktop, Claude Code, Cursor and others),
plus ask_agent, which runs the whole agent from agent.py.

  pip install mcp
  python agent_mcp.py                       # speaks MCP over stdio

Claude Code:     claude mcp add evalopt-code-reviewer -- python /full/path/to/agent_mcp.py
Claude Desktop:  add {"mcpServers": {"evalopt-code-reviewer": {"command": "python", "args": ["/full/path/to/agent_mcp.py"]}}} to its config
"""
import contextlib
import os
import sys

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x

ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"
app = Server("evalopt-code-reviewer")


def _safe_path(p):
    full = os.path.abspath(p)
    if os.path.commonpath([full, os.getcwd()]) != os.getcwd():
        raise ValueError("path is outside the working directory")
    return full


def tool_read_file(args):
    with open(_safe_path(args["path"]), encoding="utf-8") as f:
        return f.read()[:20000]


@app.tool()
def read_file(path: str) -> str:
    """Read a text file from the working directory."""
    try:
        return str(tool_read_file({"path": path}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


@app.tool()
def ask_agent(task: str) -> str:
    """Give the whole evalopt-code-reviewer agent a task and return its answer. It uses your model and API key, so it costs tokens."""
    from agent import run  # imported here so the server starts without an API key

    with contextlib.redirect_stdout(sys.stderr):  # the agent prints its steps; MCP needs stdout for itself
        return str(run(task))


if __name__ == "__main__":
    app.run()
