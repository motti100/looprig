"""chain-meeting-follow-up
Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain

Built with Loopsmith. Run it:

    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python agent.py "your task here"
"""
import json
import sys

from anthropic import Anthropic

# ---- settings (edit freely) ---------------------------------------------------
PROVIDER = "anthropic"
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096  # per model call
MAX_TURNS = 10  # tool-loop turns per pass through the loop
TOKEN_BUDGET = 200000  # hard stop for the whole run
APPROVAL = "risky"  # "none" | "risky" | "all": ask before running tools
RISKY = {"write_file", "run_python", "my_custom_tool"}
OBS_LIMIT = 6000  # max characters of one tool result the model sees
MAX_RETRIES = 5  # the SDK retries rate limits, 5xx errors and timeouts with backoff
TIMEOUT = 120  # seconds to wait for one model call
THINK = {}  # model-native extended thinking, if enabled
TRACE_FILE = "trace.jsonl"  # one JSON line per reason / act / observe event

client = Anthropic(max_retries=MAX_RETRIES, timeout=TIMEOUT)  # reads ANTHROPIC_API_KEY from the environment

SYSTEM = """You are Chain Meeting Follow Up, an AI agent.

Goal: Turn raw meeting notes into decisions, action items with owners, and a short recap email.

Answer from your own knowledge and reasoning. If you are missing information, say what is missing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""
REASON_RULES = ""

# ---- ACT: tools ---------------------------------------------------------------
TOOLS = []

# No tools selected: this agent answers from the model alone.

IMPLS = {}


# ---- provider adapter: the only code that knows which API is underneath -------------
USAGE = {"in": 0, "out": 0}
FINISHED = {"flag": False, "summary": ""}
OBS_LOG = []  # raw tool results, kept as evidence


def used_tokens():
    return USAGE["in"] + USAGE["out"]


def explain(e):
    """Say what was being called, so a bare error such as a 404 is not a mystery."""
    resp = getattr(e, "response", None)
    req = getattr(resp, "request", None)
    where = f" [{getattr(req, 'method', '')} {getattr(req, 'url', '')}]" if req is not None else ""
    body = (getattr(resp, "text", "") or "")[:500]
    return RuntimeError(f"model call failed: {type(e).__name__}: {e}{where} provider={PROVIDER} model={MODEL} {body}".strip())


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
    try:
        resp = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=system_arg, messages=messages, **kwargs)
    except Exception as e:
        raise explain(e) from e
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

        outputs = [run_call(c) for c in calls]
        add_results(messages, calls, outputs)  # results go back in for the next REASON step
    return "[stopped: MAX_TURNS reached]"


def think_and_act(task, system=SYSTEM, history=None):
    """REASON -> ACT -> OBSERVE for one agent: shape the thinking, then run the tool loop."""
    out = agent_loop(task, system=system + REASON_RULES, history=history)
    return out


# ---- shape: how the loop is wired into agents --------------------------------------
STEPS = [
    {
        "name": "Extract",
        "instruction": "Pull out the key facts, names, dates and numbers",
        "gate": "Output contains concrete facts, no opinions"
    },
    {
        "name": "Analyze",
        "instruction": "Identify patterns, risks and open questions from the facts"
    },
    {
        "name": "Write",
        "instruction": "Write a clear, structured summary for a busy reader"
    }
]


def topology(task):
    """A fixed sequence: each step's output is the next step's input, with optional gates."""
    data = task
    for i, s in enumerate(STEPS, 1):
        print(f"\n[step {i}/{len(STEPS)}] {s['name']}")
        data = think_and_act(f"{s['instruction']}\n\nInput:\n{data}")
        if s.get("gate"):
            verdict = llm("You are a strict validator.", f"Check: {s['gate']}\n\nOutput:\n{data}\n\nReply 'PASS' or 'FAIL: reason'.")
            if verdict.strip().upper().startswith("FAIL"):
                return f"[chain stopped at '{s['name']}'] {verdict}"
    return data


def run(task):
    return topology(task)


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "Notes: we agreed to ship v2 on the 14th. Priya owns the migration. Tom to confirm pricing by Friday."
    print("\n" + run(task))
    print(f"\n[tokens used: {used_tokens()}]")
