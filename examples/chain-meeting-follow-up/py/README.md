# Chain Meeting Follow Up

Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain

Built with [LoopRig](.) v3.6.7. Provider: Anthropic (Claude), model `claude-sonnet-5-5`.

## Run it

```
pip install anthropic
export ANTHROPIC_API_KEY="..."
python agent.py "Notes: we agreed to ship v2 on the 14th. Priya owns the migration. Tom to confirm pricing by Friday."
```

Give it files or pictures: `python agent.py "your task" --file notes.txt --image photo.png`

## What is in this folder

- `agent.py`: the agent. Settings are at the top of the file.
- `evals.py`: a small regression suite. Add cases as you find failures.
- `smoke_test.py`: checks that your provider keys can do tool calling.
- `TROUBLESHOOTING.md`: what each error means and how to fix it. Start with `python agent.py --doctor`.
- `blueprint.json`: load it back into LoopRig to change the design.
- `AGENTS.md`: short notes for coding agents and teammates (how to run, layout, conventions).
- `server.py`, `Dockerfile`, `.env.example`, `requirements.txt`: run it as an HTTP service.
- `agent_langgraph.py`, `agent_agents_sdk.py`: the same agent on two popular frameworks (basic features only).
- `agent_mcp.py`: your agent's tools, and the agent itself (ask_agent), as an MCP server for Claude Desktop, Claude Code and Cursor.

## Before you rely on it

- Read the code. Tools that write files, run code or reach the web deserve a careful look.
- Keep approval on while you learn how the agent behaves. A server runs with approval off and risky tools removed unless you set `ALLOW_RISKY_TOOLS=1`.
- Hard limits (turns, tokens) are constants near the top of the agent. Lower them while testing.
- Model names change. If a provider retires one, edit `MODEL`.
