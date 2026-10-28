"""goal-research-brief (OpenAI Agents SDK version)
Reason: plan first | Act: read_file, write_file, run_python | Observe: log | Decide: stop when done | Shape: goal mode

Exported by Loopsmith. This keeps your model, system prompt, tools, approval setting and turn limit,
and hands the loop itself to the OpenAI Agents SDK. Loopsmith-only techniques (tree of thoughts,
reflection, team shapes, MCP, structured output) are not carried over: use the main agent file for those.

  pip install "openai-agents[litellm]"
  export ANTHROPIC_API_KEY=...
  python agent_agents_sdk.py "your task"
"""
import json
import os
import subprocess
import sys

from agents import Agent, ModelSettings, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096
MAX_TURNS = 10  # model calls allowed in one run
SYSTEM = """You are Goal Research Brief, an AI agent.

Goal: Research a topic on the web and write a short, sourced brief with key findings and open questions.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file, write_file, run_python. Use a tool only when it moves the task forward, and read each result before continuing.

You run in rounds. Your notes are saved in progress.md between rounds. Make real progress each round, and call finish only when the goal is fully met.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""


def _safe_path(p):
    full = os.path.abspath(p)
    if not full.startswith(os.getcwd()):
        raise ValueError("path is outside the working directory")
    return full


def tool_read_file(args):
    with open(_safe_path(args["path"]), encoding="utf-8") as f:
        return f.read()[:20000]


def tool_write_file(args):
    path = os.path.abspath(args["path"])
    if not path.startswith(os.getcwd()):
        raise ValueError("path is outside the working directory")
    with open(path, "w", encoding="utf-8") as f:
        f.write(args["content"])
    return f"wrote {len(args['content'])} characters to {args['path']}"


def tool_run_python(args):
    # Runs on YOUR machine. Keep approval on, or move this into a sandbox/container.
    r = subprocess.run([sys.executable, "-c", args["code"]], capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr)[-6000:]


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


@function_tool
def write_file(path: str, content: str) -> str:
    """Write text to a file in the working directory, replacing its contents."""
    if not approved("write_file", {"path": path, "content": content}):
        return "error: the user declined this action"
    try:
        return str(tool_write_file({"path": path, "content": content}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"


@function_tool
def run_python(code: str) -> str:
    """Run a short Python 3 script and return what it prints (stdout and stderr). Use print() to show results."""
    if not approved("run_python", {"code": code}):
        return "error: the user declined this action"
    try:
        return str(tool_run_python({"code": code}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"

agent = Agent(
    name="goal-research-brief",
    instructions=SYSTEM,
    model=LitellmModel(model="anthropic/" + MODEL, api_key=os.environ.get("ANTHROPIC_API_KEY")),
    model_settings=ModelSettings(max_tokens=MAX_TOKENS),
    tools=[read_file, write_file, run_python],
)


def run(task):
    return Runner.run_sync(agent, task, max_turns=MAX_TURNS).final_output


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "What are the main trade-offs between SQLite and Postgres for a small SaaS product?"))
