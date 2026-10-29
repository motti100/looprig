"""react-research-brief as an MCP server
Reason: ReAct | Act: web_search, fetch_url | Observe: raw | Decide: stop when done | Shape: single agent

Exported by LoopRig. It offers this agent's tools to any MCP client (Claude Desktop, Claude Code, Cursor and others),
plus ask_agent, which runs the whole agent from agent.py.

  pip install mcp
  python agent_mcp.py                       # speaks MCP over stdio

Claude Code:     claude mcp add react-research-brief -- python /full/path/to/agent_mcp.py
Claude Desktop:  add {"mcpServers": {"react-research-brief": {"command": "python", "args": ["/full/path/to/agent_mcp.py"]}}} to its config
"""
import contextlib
import json
import os
import sys
import urllib.request

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x

ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"
app = Server("react-research-brief")


def tool_web_search(args):
    # Tavily (https://tavily.com) has a free tier. Swap in Brave, SerpAPI or Bing the same way.
    body = json.dumps({"query": args["query"], "max_results": 5}).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["TAVILY_API_KEY"]}
    req = urllib.request.Request("https://api.tavily.com/search", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    return "\n\n".join(f"{x['title']}\n{x['url']}\n{x['content']}" for x in data.get("results", [])) or "no results"


def tool_fetch_url(args):
    req = urllib.request.Request(args["url"], headers={"User-Agent": "agent/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(200_000).decode("utf-8", "ignore")[:8000]


@app.tool()
def web_search(query: str) -> str:
    """Search the web and return the top results with titles, URLs and short snippets."""
    try:
        return str(tool_web_search({"query": query}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


@app.tool()
def fetch_url(url: str) -> str:
    """Fetch a web page by URL and return its text content (truncated)."""
    try:
        return str(tool_fetch_url({"url": url}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


@app.tool()
def ask_agent(task: str) -> str:
    """Give the whole react-research-brief agent a task and return its answer. It uses your model and API key, so it costs tokens."""
    from agent import run  # imported here so the server starts without an API key

    with contextlib.redirect_stdout(sys.stderr):  # the agent prints its steps; MCP needs stdout for itself
        return str(run(task))


if __name__ == "__main__":
    app.run()
