"""rag-support-answers
Reason: ReAct | Act: search_docs | Observe: compress | Decide: ground | Shape: single agent

Built with Loopsmith. Run it:

    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python agent.py "your task here"
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from anthropic import Anthropic

# ---- settings (edit freely) ---------------------------------------------------
PROVIDER = "anthropic"
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096  # per model call
MAX_TURNS = 10  # tool-loop turns per pass through the loop
TOKEN_BUDGET = 200000  # hard stop for the whole run
APPROVAL = "none"  # "none" | "risky" | "all": ask before running tools
RISKY = {"write_file", "run_python", "my_custom_tool"}
OBS_LIMIT = 6000  # max characters of one tool result the model sees
MAX_RETRIES = 5  # the SDK retries rate limits, 5xx errors and timeouts with backoff
TIMEOUT = 120  # seconds to wait for one model call
THINK = {}  # model-native extended thinking, if enabled
TRACE_FILE = "trace.jsonl"  # one JSON line per reason / act / observe event

client = Anthropic(max_retries=MAX_RETRIES, timeout=TIMEOUT)  # reads ANTHROPIC_API_KEY from the environment

SYSTEM = """You are Rag Support Answers, an AI agent.

Goal: Answer customer questions using our help documents, and flag anything that needs a human.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: search_docs. Use a tool only when it moves the task forward, and read each result before continuing.

Ground every answer in what search_docs returns and name the file each claim came from. If the documents do not contain the answer, say so instead of guessing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""
REASON_RULES = "\n\nWork in a Reason, Act, Observe loop. Before every tool call write one short 'Thought:' line saying why. After each result write 'Observation:' with what you learned. When you can answer, write 'Final Answer:' followed by the answer."
COMPRESS_AT = 1500  # tool results longer than this get summarized
GROUNDER = "You check answers against evidence. Be literal and strict."

# ---- ACT: tools ---------------------------------------------------------------
TOOLS = [
    {
        "name": "search_docs",
        "description": "Search the local documents and return the most relevant passages with their file names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to look for"
                }
            },
            "required": [
                "query"
            ]
        }
    }
]

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

IMPLS = {
    "search_docs": tool_search_docs,
}


# ---- provider adapter: the only code that knows which API is underneath -------------
USAGE = {"in": 0, "out": 0}
FINISHED = {"flag": False, "summary": ""}
OBS_LOG = []  # raw tool results, kept as evidence


def used_tokens():
    return USAGE["in"] + USAGE["out"]


def trace(kind, **data):
    """Append one event to trace.jsonl so every run can be replayed and audited."""
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": kind, "tokens": used_tokens(), **data}, default=str) + "\n")


def chat(system, messages, tools=None, think=False):
    """One model call. Appends the assistant turn to `messages` and returns a neutral reply."""
    kwargs = {"tools": tools} if tools else {}
    # Prompt caching: the system prompt and tool list are re-sent every turn, so cache them.
    system_arg = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if think:
        kwargs.update(THINK)
    resp = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=system_arg, messages=messages, **kwargs)
    USAGE["in"] += resp.usage.input_tokens
    USAGE["out"] += resp.usage.output_tokens
    messages.append({"role": "assistant", "content": resp.content})
    return {
        "text": "".join(b.text for b in resp.content if b.type == "text"),
        "calls": [{"id": b.id, "name": b.name, "args": b.input} for b in resp.content if b.type == "tool_use"],
        "paused": resp.stop_reason == "pause_turn",  # a server-side tool (web search) needs another pass
    }


def add_results(messages, calls, outputs):
    blocks = [{"type": "tool_result", "tool_use_id": c["id"], "content": o} for c, o in zip(calls, outputs)]
    messages.append({"role": "user", "content": blocks})


def llm(system, prompt):
    """One plain model call with no tools. Used for planning, critique and voting."""
    return chat(system, [{"role": "user", "content": prompt}])["text"]


def parse_json(text):
    spans = sorted((text.find(o), c) for o, c in (("[", "]"), ("{", "}")) if o in text)
    for start, close in spans:
        try:
            return json.loads(text[start : text.rfind(close) + 1])
        except json.JSONDecodeError:
            continue
    raise ValueError("no JSON found in: " + text[:200])


def call_tool(name, args):
    fn = IMPLS.get(name)
    if fn is None:
        return f"error: unknown tool {name}"
    risky = name in RISKY
    if APPROVAL == "all" or (APPROVAL == "risky" and risky):
        if input(f"\n  approve {name}({json.dumps(args)[:200]})? [y/N] ").strip().lower() != "y":
            return "error: the user declined this action"
    try:
        return str(fn(args))
    except Exception as e:  # tool errors go back to the model so it can adjust
        return f"error: {e}"


# ---- OBSERVE ----------------------------------------------------------------------
def observe(name, text, task):
    """Decide what the model gets to see after a tool runs."""
    OBS_LOG.append(f"[{name}] {text[:4000]}")
    if len(text) > COMPRESS_AT:
        text = llm(
            "You compress tool output without losing facts.",
            f"Task context: {task}\n\nTool output:\n{text[:20000]}\n\nKeep only what helps the task: facts, numbers, names, errors. About 150 words.",
        )
    return text[:OBS_LIMIT]


# ---- the loop: REASON -> ACT -> OBSERVE -> DECIDE whether to go round again ---------
def agent_loop(task, system=SYSTEM, history=None, tools=None):
    tools = TOOLS if tools is None else tools
    messages = history if history is not None else []
    messages.append({"role": "user", "content": task})
    for turn in range(1, MAX_TURNS + 1):
        if used_tokens() > TOKEN_BUDGET:
            return "[stopped: token budget reached]"
        reply = chat(system, messages, tools, think=True)  # REASON
        if reply["text"].strip():
            print(f"[reason {turn}] {reply['text'].strip()[:300]}")
            trace("reason", turn=turn, text=reply["text"].strip()[:2000])
        if reply["paused"]:
            continue
        calls = reply["calls"]
        if not calls:  # DECIDE: no more actions requested, so the model is done
            return reply["text"]
        for c in calls:
            if c["name"] == "finish":
                FINISHED.update(flag=True, summary=c["args"].get("summary", ""))
                return FINISHED["summary"]

        def run_call(c):
            print(f"[act {turn}] {c['name']}({json.dumps(c['args'])[:120]})")  # ACT
            trace("act", turn=turn, tool=c["name"], input=c["args"])
            raw = call_tool(c["name"], c["args"])
            seen = observe(c["name"], raw, task)  # OBSERVE
            trace("observe", turn=turn, tool=c["name"], chars=len(raw), shown=len(seen))
            return seen

        if len(calls) > 1 and APPROVAL == "none":  # independent calls in one turn run at the same time
            with ThreadPoolExecutor(max_workers=len(calls)) as pool:
                outputs = list(pool.map(run_call, calls))
        else:
            outputs = [run_call(c) for c in calls]
        add_results(messages, calls, outputs)  # results go back in for the next REASON step
    return "[stopped: MAX_TURNS reached]"


def think_and_act(task, system=SYSTEM, history=None):
    """REASON -> ACT -> OBSERVE for one agent: shape the thinking, then run the tool loop."""
    out = agent_loop(task, system=system + REASON_RULES, history=history)
    out = out.split("Final Answer:")[-1].strip()
    return out


# ---- shape: how the loop is wired into agents --------------------------------------
def topology(task, history=None):
    return think_and_act(task, history=history)


# ---- DECIDE: is this good enough to return? --------------------------------------
def ground(task, draft):
    """Check every claim against what the tools actually returned."""
    evidence = "\n\n".join(OBS_LOG[-12:])[:12000] or "(no tool results)"
    ask = f"Question: {task}\n\nAnswer:\n{draft}\n\nEvidence:\n{evidence}\n\nList every claim in the answer that the evidence does not support. If all are supported, reply exactly SUPPORTED."
    verdict = llm(GROUNDER, ask)
    print(f"  [ground] {verdict[:200]}")
    if verdict.strip().startswith("SUPPORTED"):
        return draft
    return think_and_act(f"Task: {task}\n\nDraft:\n{draft}\n\nUnsupported claims:\n{verdict}\n\nRewrite the answer so every claim is backed by the evidence, or clearly marked uncertain.")


def improve(task, draft):
    draft = ground(task, draft)
    return draft


def run(task):
    return improve(task, topology(task))


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "A customer asks how to change the email address on their account."
    print("\n" + run(task))
    print(f"\n[tokens used: {used_tokens()}]")
