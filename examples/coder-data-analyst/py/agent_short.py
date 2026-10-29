"""coder-data-analyst: the short version.

What it does: Answer questions about a CSV file by writing and running Python, then explain the result in plain language..

The loop has four moves, marked in the code:
  REASON   the model reads the conversation and decides what to do
  ACT      it asks to use a tool
  OBSERVE  we run the tool and give the result back
  DECIDE   if it asks for nothing more, it is done

Left out of this short version: running Python, plan first, the evaluator. The full agent has them.

Run it:
    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python agent_short.py "Which month had the highest revenue in sales.csv, and by how much did it beat the average?"
"""
import os, sys
from anthropic import Anthropic
import ast, operator

MODEL = "claude-sonnet-5-5"
MAX_TURNS = 10  # a hard stop, so a confused agent cannot run forever
SYSTEM = """You are Coder Data Analyst, an AI agent.

Goal: Answer questions about a CSV file by writing and running Python, then explain the result in plain language.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: calculator, read_file. Use a tool only when it moves the task forward, and read each result before continuing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""

# ---- TOOLS: a description the model reads, and a function we run
TOOLS = [
    {"name":"calculator","description":"Evaluate an arithmetic expression such as (12.5 * 4) / 3.","input_schema":{"type":"object","properties":{"expression":{"type":"string"}},"required":["expression"]}},
    {"name":"read_file","description":"Read a text file from the working directory.","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}
]

def calculator(expression):
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg}
    def calc(n):  # only numbers and arithmetic are allowed, never arbitrary code
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops: return ops[type(n.op)](calc(n.left), calc(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops: return ops[type(n.op)](calc(n.operand))
        raise ValueError("only arithmetic is allowed")
    return calc(ast.parse(expression, mode="eval").body)

def safe_path(path):  # tools may only touch files inside this folder
    full = os.path.realpath(path or ".")
    if os.path.commonpath([full, os.getcwd()]) != os.getcwd(): raise ValueError("outside the working folder")
    return full

def read_file(path):
    return open(safe_path(path), encoding="utf-8").read()[:20000]

RUN = {"calculator": calculator, "read_file": read_file}

# ---- THE LOOP
client = Anthropic()  # reads ANTHROPIC_API_KEY
task = sys.argv[1] if len(sys.argv) > 1 else "Which month had the highest revenue in sales.csv, and by how much did it beat the average?"
messages = [{"role": "user", "content": task}]

for turn in range(MAX_TURNS):
    # REASON: the model reads everything so far and decides what to do
    reply = client.messages.create(model=MODEL, max_tokens=4096, system=SYSTEM, tools=TOOLS, messages=messages)
    messages.append({"role": "assistant", "content": reply.content})
    calls = [b for b in reply.content if b.type == "tool_use"]

    # DECIDE: no tool requested means the model has its answer
    if not calls:
        print("".join(b.text for b in reply.content if b.type == "text"))
        break

    results = []
    for call in calls:
        # ACT: run the tool the model asked for
        try: output = str(RUN[call.name](**call.input))
        except Exception as e: output = f"error: {e}"  # the model sees the error and can recover
        # OBSERVE: give the result back so the next turn can use it
        results.append({"type": "tool_result", "tool_use_id": call.id, "content": output})
    messages.append({"role": "user", "content": results})
else:
    print("Stopped: reached MAX_TURNS without a final answer.")
