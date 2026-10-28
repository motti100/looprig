"""rag-support-answers (LangGraph version)
Reason: ReAct | Act: search_docs | Observe: compress | Decide: ground | Shape: single agent

Exported by Looprig. This keeps your model, system prompt, tools, approval setting and turn limit,
and hands the loop itself to LangGraph. Looprig-only techniques (tree of thoughts, reflection,
team shapes, MCP, structured output) are not carried over: use the main agent file for those.

  pip install langchain langgraph langchain-anthropic
  export ANTHROPIC_API_KEY=...
  python agent_langgraph.py "your task"
"""
import json
import os
import sys

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096
MAX_TURNS = 10  # model calls allowed in one run
SYSTEM = """You are Rag Support Answers, an AI agent.

Goal: Answer customer questions using our help documents, and flag anything that needs a human.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: search_docs. Use a tool only when it moves the task forward, and read each result before continuing.

Ground every answer in what search_docs returns and name the file each claim came from. If the documents do not contain the answer, say so instead of guessing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""


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


APPROVAL = "none"  # "none" | "risky" | "all": ask before running tools
RISKY = {"write_file", "run_python", "my_custom_tool"}


def approved(name, args):
    if APPROVAL == "all" or (APPROVAL == "risky" and name in RISKY):
        return input(f"\n  approve {name}({json.dumps(args)[:200]})? [y/N] ").strip().lower() == "y"
    return True


@tool
def search_docs(query: str) -> str:
    """Search the local documents and return the most relevant passages with their file names."""
    if not approved("search_docs", {"query": query}):
        return "error: the user declined this action"
    try:
        return str(tool_search_docs({"query": query}))
    except Exception as e:  # errors go back to the model so it can adjust
        return f"error: {e}"

model = init_chat_model("anthropic:" + MODEL, max_tokens=MAX_TOKENS)
agent = create_agent(model, tools=[search_docs], system_prompt=SYSTEM, name="rag-support-answers")


def run(task):
    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, {"recursion_limit": MAX_TURNS * 2 + 1})
    return result["messages"][-1].text


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "A customer asks how to change the email address on their account."))
