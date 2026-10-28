"""evalopt-code-reviewer (OpenAI Agents SDK version)
Reason: direct | Act: read_file | Observe: raw | Decide: evaluate >= 8 | Shape: single agent

Exported by Looprig. This keeps your model, system prompt, tools, approval setting and turn limit,
and hands the loop itself to the OpenAI Agents SDK. Looprig-only techniques (tree of thoughts,
reflection, team shapes, MCP, structured output) are not carried over: use the main agent file for those.

  pip install "openai-agents[litellm]"
  export ANTHROPIC_API_KEY=...
  python agent_agents_sdk.py "your task"
"""
import json
import os
import sys

from agents import Agent, ModelSettings, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096
MAX_TURNS = 10  # model calls allowed in one run
SYSTEM = """You are Evalopt Code Reviewer, an AI agent.

Goal: Review a code file for bugs, security issues and unclear naming. Report findings ranked by severity with suggested fixes.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file. Use a tool only when it moves the task forward, and read each result before continuing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""


def _safe_path(p):
    full = os.path.abspath(p)
    if os.path.commonpath([full, os.getcwd()]) != os.getcwd():
        raise ValueError("path is outside the working directory")
    return full


def tool_read_file(args):
    with open(_safe_path(args["path"]), encoding="utf-8") as f:
        return f.read()[:20000]


APPROVAL = "risky"  # "none" | "risky" | "all": ask before running tools
RISKY = {"write_file", "run_python", "my_custom_tool"}


def approved(name, args):
    if APPROVAL == "all" or (APPROVAL == "risky" and name in RISKY):
        return input(f"\n  approve {name}({json.dumps(args)[:200]})? [y/N] ").strip().lower() == "y"
    return True


@function_tool
def read_file(path: str) -> str:
    """Read a text file from the working directory."""
    if not approved("read_file", {"path": path}):
        return "error: the user declined this action"
    try:
        return str(tool_read_file({"path": path}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"

agent = Agent(
    name="evalopt-code-reviewer",
    instructions=SYSTEM,
    model=LitellmModel(model="anthropic/" + MODEL, api_key=os.environ.get("ANTHROPIC_API_KEY")),
    model_settings=ModelSettings(max_tokens=MAX_TOKENS),
    tools=[read_file],
)


def run(task):
    return Runner.run_sync(agent, task, max_turns=MAX_TURNS).final_output


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Review app.py and list the three most serious problems."))
