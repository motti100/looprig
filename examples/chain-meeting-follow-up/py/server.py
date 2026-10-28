"""HTTP wrapper for chain-meeting-follow-up. Run: uvicorn server:app --port 8000

POST /run   {"task": "..."}                       -> {"answer": "...", "tokens": 123}
GET  /health
"""
import os
import threading

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import agent

API_TOKEN = os.environ.get("AGENT_API_TOKEN")
ALLOW_RISKY = os.environ.get("ALLOW_RISKY_TOOLS") == "1"

# There is no terminal to ask in, so approval prompts are off. To stay safe, tools that can act
# (write files, run code, MCP servers) are removed unless you opt in with ALLOW_RISKY_TOOLS=1.
agent.APPROVAL = "none"
if not ALLOW_RISKY:
    risky = set(agent.RISKY) | set(getattr(getattr(agent, "MCP", None), "sessions", {}))
    agent.TOOLS[:] = [t for t in agent.TOOLS if t["name"] not in risky]
    for name in risky:
        agent.IMPLS.pop(name, None)

app = FastAPI(title="chain-meeting-follow-up")
LOCK = threading.Lock()  # the agent keeps token counters in module state, so run one request at a time


class RunRequest(BaseModel):
    task: str


def check(authorization):
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="missing or wrong bearer token")


def reset():
    agent.USAGE.update({"in": 0, "out": 0})
    agent.FINISHED.update(flag=False, summary="")
    agent.OBS_LOG.clear()


@app.get("/health")
def health():
    return {"ok": True, "tools": [t["name"] for t in agent.TOOLS]}


@app.post("/run")
def run(req: RunRequest, authorization: str | None = Header(default=None)):
    check(authorization)
    with LOCK:
        reset()
        answer = agent.run(req.task)
        return {"answer": answer, "tokens": agent.used_tokens()}
