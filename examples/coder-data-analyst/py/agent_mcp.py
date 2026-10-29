"""coder-data-analyst as an MCP server
Reason: plan first | Act: calculator, read_file, run_python | Observe: raw | Decide: evaluate >= 8 | Shape: single agent

Exported by LoopRig. It offers this agent's tools to any MCP client (Claude Desktop, Claude Code, Cursor and others),
plus ask_agent, which runs the whole agent from agent.py.

  pip install mcp
  python agent_mcp.py                       # speaks MCP over stdio

Claude Code:     claude mcp add coder-data-analyst -- python /full/path/to/agent_mcp.py
Claude Desktop:  add {"mcpServers": {"coder-data-analyst": {"command": "python", "args": ["/full/path/to/agent_mcp.py"]}}} to its config
"""
import ast
import contextlib
import operator as op
import os
import subprocess
import sys

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x

ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"
app = Server("coder-data-analyst")


_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def tool_calculator(args):
    return _eval(ast.parse(args["expression"], mode="eval").body)


def _safe_path(p):
    full = os.path.abspath(p)
    if os.path.commonpath([full, os.getcwd()]) != os.getcwd():
        raise ValueError("path is outside the working directory")
    return full


def tool_read_file(args):
    with open(_safe_path(args["path"]), encoding="utf-8") as f:
        return f.read()[:20000]


def tool_run_python(args):
    # Runs on YOUR machine. Keep approval on, or move this into a sandbox/container.
    r = subprocess.run([sys.executable, "-c", args["code"]], capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr)[-6000:]


@app.tool()
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression such as (12.5 * 4) / 3."""
    try:
        return str(tool_calculator({"expression": expression}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


@app.tool()
def read_file(path: str) -> str:
    """Read a text file from the working directory."""
    try:
        return str(tool_read_file({"path": path}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


# These tools can change files or run code. They are off unless you set ALLOW_RISKY_TOOLS=1.
if ALLOW_RISKY:
    @app.tool()
    def run_python(code: str) -> str:
        """Run a short Python 3 script and return what it prints (stdout and stderr). Use print() to show results."""
        try:
            return str(tool_run_python({"code": code}))
        except Exception as e:  # errors go back to the client
            return f"error: {e}"


@app.tool()
def ask_agent(task: str) -> str:
    """Give the whole coder-data-analyst agent a task and return its answer. It uses your model and API key, so it costs tokens."""
    from agent import run  # imported here so the server starts without an API key

    with contextlib.redirect_stdout(sys.stderr):  # the agent prints its steps; MCP needs stdout for itself
        return str(run(task))


if __name__ == "__main__":
    app.run()
