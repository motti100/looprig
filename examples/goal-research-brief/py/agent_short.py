"""goal-research-brief: the short version.

What it does: Research a topic on the web and write a short, sourced brief with key findings and open questions..

The loop has four moves, marked in the code:
  REASON   the model reads the conversation and decides what to do
  ACT      it asks to use a tool
  OBSERVE  we run the tool and give the result back
  DECIDE   if it asks for nothing more, it is done

Left out of this short version: running Python, the goal loop, plan first, result compression and logging. The full agent has them.

Run it:
    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python agent_short.py "What are the main trade-offs between SQLite and Postgres for a small SaaS product?"
"""
import os, sys
from anthropic import Anthropic

MODEL = "claude-sonnet-5-5"
MAX_TURNS = 10  # a hard stop, so a confused agent cannot run forever
SYSTEM = """You are Goal Research Brief, an AI agent.

Goal: Research a topic on the web and write a short, sourced brief with key findings and open questions.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file, write_file. Use a tool only when it moves the task forward, and read each result before continuing.

You run in rounds. Your notes are saved in progress.md between rounds. Make real progress each round, and call finish only when the goal is fully met.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""

# ---- TOOLS: a description the model reads, and a function we run
TOOLS = [
    {"name":"read_file","description":"Read a text file from the working directory.","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"write_file","description":"Write text to a file in the working directory, replacing its contents.","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}
]

def safe_path(path):  # tools may only touch files inside this folder
    full = os.path.realpath(path or ".")
    if os.path.commonpath([full, os.getcwd()]) != os.getcwd(): raise ValueError("outside the working folder")
    return full

def read_file(path):
    return open(safe_path(path), encoding="utf-8").read()[:20000]

def write_file(path, content):
    full = safe_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)
    return f"wrote {len(content)} characters to {path}"

RUN = {"read_file": read_file, "write_file": write_file}

# ---- THE LOOP
client = Anthropic()  # reads ANTHROPIC_API_KEY
task = sys.argv[1] if len(sys.argv) > 1 else "What are the main trade-offs between SQLite and Postgres for a small SaaS product?"
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
        if call.name in ("write_file",) and input(f"Allow {call.name} {call.input}? [y/N] ").lower() != "y":
            output = "error: the user declined this action"
        else:
            try: output = str(RUN[call.name](**call.input))
            except Exception as e: output = f"error: {e}"  # the model sees the error and can recover
        # OBSERVE: give the result back so the next turn can use it
        results.append({"type": "tool_result", "tool_use_id": call.id, "content": output})
    messages.append({"role": "user", "content": results})
else:
    print("Stopped: reached MAX_TURNS without a final answer.")
