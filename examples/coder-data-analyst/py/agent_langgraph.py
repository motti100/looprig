"""coder-data-analyst (LangGraph version)
Reason: plan first | Act: calculator, read_file, run_python | Observe: raw | Decide: evaluate >= 8 | Shape: single agent

Exported by Looprig. This keeps your model, system prompt, tools, approval setting and turn limit,
and hands the loop itself to LangGraph. Looprig-only techniques (tree of thoughts, reflection,
team shapes, MCP, structured output) are not carried over: use the main agent file for those.

  pip install langchain langgraph langchain-anthropic
  export ANTHROPIC_API_KEY=...
  python agent_langgraph.py "your task"
"""
import ast
import json
import operator as op
import os
import subprocess
import sys

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096
MAX_TURNS = 10  # model calls allowed in one run
SYSTEM = """You are Coder Data Analyst, an AI agent.

Goal: Answer questions about a CSV file by writing and running Python, then explain the result in plain language.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: calculator, read_file, run_python. Use a tool only when it moves the task forward, and read each result before continuing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""


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
    if not full.startswith(os.getcwd()):
        raise ValueError("path is outside the working directory")
    return full


def tool_read_file(args):
    with open(_safe_path(args["path"]), encoding="utf-8") as f:
        return f.read()[:20000]


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


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression such as (12.5 * 4) / 3."""
    if not approved("calculator", {"expression": expression}):
        return "error: the user declined this action"
    try:
        return str(tool_calculator({"expression": expression}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"


@tool
def read_file(path: str) -> str:
    """Read a text file from the working directory."""
    if not approved("read_file", {"path": path}):
        return "error: the user declined this action"
    try:
        return str(tool_read_file({"path": path}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"


@tool
def run_python(code: str) -> str:
    """Run a short Python 3 script and return what it prints (stdout and stderr). Use print() to show results."""
    if not approved("run_python", {"code": code}):
        return "error: the user declined this action"
    try:
        return str(tool_run_python({"code": code}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"

model = init_chat_model("anthropic:" + MODEL, max_tokens=MAX_TOKENS)
agent = create_agent(model, tools=[calculator, read_file, run_python], system_prompt=SYSTEM, name="coder-data-analyst")


def run(task):
    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, {"recursion_limit": MAX_TURNS * 2 + 1})
    return result["messages"][-1].text


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Which month had the highest revenue in sales.csv, and by how much did it beat the average?"))
