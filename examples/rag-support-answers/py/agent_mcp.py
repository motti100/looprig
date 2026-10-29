"""rag-support-answers as an MCP server
Reason: ReAct | Act: search_docs | Observe: compress | Decide: ground | Shape: single agent

Exported by LoopRig. It offers this agent's tools to any MCP client (Claude Desktop, Claude Code, Cursor and others),
plus ask_agent, which runs the whole agent from agent.py.

  pip install mcp
  python agent_mcp.py                       # speaks MCP over stdio

Claude Code:     claude mcp add rag-support-answers -- python /full/path/to/agent_mcp.py
Claude Desktop:  add {"mcpServers": {"rag-support-answers": {"command": "python", "args": ["/full/path/to/agent_mcp.py"]}}} to its config
"""
import contextlib
import os
import sys

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x

ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"
app = Server("rag-support-answers")


DOCS_DIR = "docs"  # put .md / .txt files here
TOP_K = 4


def tool_search_docs(args):
    # Keyword scoring keeps this dependency-free. Swap in embeddings or a vector DB for real corpora.
    words = [w for w in args["query"].lower().split() if len(w) > 2]
    hits = []
    for root, _, files in os.walk(DOCS_DIR):
        for fn in files:
            if fn.endswith((".md", ".txt")):
                path = os.path.join(root, fn)
                text = open(path, encoding="utf-8", errors="ignore").read()
                for i in range(0, len(text), 800):
                    chunk = text[i : i + 800]
                    score = sum(w in chunk.lower() for w in words)
                    if score:
                        hits.append((score, path, chunk))
    hits.sort(reverse=True)
    return "\n\n".join(f"[{p}]\n{c}" for _, p, c in hits[:TOP_K]) or "no matches"


@app.tool()
def search_docs(query: str) -> str:
    """Search the local documents and return the most relevant passages with their file names."""
    try:
        return str(tool_search_docs({"query": query}))
    except Exception as e:  # errors go back to the client
        return f"error: {e}"


@app.tool()
def ask_agent(task: str) -> str:
    """Give the whole rag-support-answers agent a task and return its answer. It uses your model and API key, so it costs tokens."""
    from agent import run  # imported here so the server starts without an API key

    with contextlib.redirect_stdout(sys.stderr):  # the agent prints its steps; MCP needs stdout for itself
        return str(run(task))


if __name__ == "__main__":
    app.run()
