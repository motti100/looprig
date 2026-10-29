"""rag-support-answers: the short version.

What it does: Answer customer questions using our help documents, and flag anything that needs a human..

The loop has four moves, marked in the code:
  REASON   the model reads the conversation and decides what to do
  ACT      it asks to use a tool
  OBSERVE  we run the tool and give the result back
  DECIDE   if it asks for nothing more, it is done

Left out of this short version: searching your documents, the grounding check, result compression and logging. The full agent has them.

Run it:
    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python agent_short.py "A customer asks how to change the email address on their account."
"""
import os, sys
from anthropic import Anthropic

MODEL = "claude-sonnet-5-5"
MAX_TURNS = 10  # a hard stop, so a confused agent cannot run forever
SYSTEM = """You are Rag Support Answers, an AI agent.

Goal: Answer customer questions using our help documents, and flag anything that needs a human.

Answer from your own knowledge and reasoning. If you are missing information, say what is missing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""

# ---- TOOLS: a description the model reads, and a function we run
TOOLS = [

]

RUN = {}

# ---- THE LOOP
client = Anthropic()  # reads ANTHROPIC_API_KEY
task = sys.argv[1] if len(sys.argv) > 1 else "A customer asks how to change the email address on their account."
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
