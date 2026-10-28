/**
 * chain-meeting-follow-up
 * Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain
 *
 * Built with Loopsmith. Run it:
 *   npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
 *   export ANTHROPIC_API_KEY=...
 *   npx tsx agent.ts "your task here"
 */
import Anthropic from "@anthropic-ai/sdk";
import fs from "node:fs";
import readline from "node:readline/promises";

// ---- settings (edit freely) ---------------------------------------------------
const PROVIDER = "anthropic";
const MODEL = "claude-sonnet-5-5";
const MAX_TOKENS = 4096; // per model call
const MAX_TURNS = 10; // tool-loop turns per pass through the loop
const TOKEN_BUDGET = 200000; // hard stop for the whole run
let APPROVAL = "risky" as "none" | "risky" | "all"; // ask before running tools
const RISKY = new Set(["write_file", "run_python", "my_custom_tool"]);
const OBS_LIMIT = 6000; // max characters of one tool result the model sees
const MAX_RETRIES = 5; // the SDK retries rate limits, 5xx errors and timeouts with backoff
const TIMEOUT_S = 120; // seconds to wait for one model call
const THINK: Record<string, unknown> = {}; // model-native extended thinking, if enabled
const TRACE_FILE = "trace.jsonl"; // one JSON line per reason / act / observe event

const client = new Anthropic({ maxRetries: MAX_RETRIES, timeout: TIMEOUT_S * 1000 }); // reads ANTHROPIC_API_KEY from the environment

const SYSTEM = `You are Chain Meeting Follow Up, an AI agent.

Goal: Turn raw meeting notes into decisions, action items with owners, and a short recap email.

Answer from your own knowledge and reasoning. If you are missing information, say what is missing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it.`;
const REASON_RULES = "";

// ---- ACT: tools ---------------------------------------------------------------
const TOOLS: any[] = [];

// No tools selected: this agent answers from the model alone.

const IMPLS: Record<string, (a: any) => any> = {};


// ---- provider adapter: the only code that knows which API is underneath -------------
const USAGE = { in: 0, out: 0 };
const FINISHED = { flag: false, summary: "" };
const OBS_LOG: string[] = []; // raw tool results, kept as evidence

const usedTokens = () => USAGE.in + USAGE.out;

/** Say what was being called, so a bare error such as a 404 is not a mystery. */
function explain(e: any): Error {
  return new Error("model call failed: " + (e?.message ?? e) + " [provider=" + PROVIDER + " model=" + MODEL + "]");
}

async function ask(question: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    return await rl.question(question);
  } finally {
    rl.close();
  }
}

/** Append one event to trace.jsonl so every run can be replayed and audited. */
function trace(kind: string, data: Record<string, unknown> = {}) {
  fs.appendFileSync(TRACE_FILE, JSON.stringify({ kind, tokens: usedTokens(), ...data }) + "\n");
}

type Call = { id: string; name: string; args: any };
type Reply = { text: string; calls: Call[]; paused: boolean };

/** One model call. Appends the assistant turn to `messages` and returns a neutral reply. */
async function chat(system: string, messages: any[], tools: any[] = [], think = false): Promise<Reply> {
  // Prompt caching: the system prompt and tool list are re-sent every turn, so cache them.
  const systemArg: any = [{ type: "text", text: system, cache_control: { type: "ephemeral" } }];
  const params: any = { model: MODEL, max_tokens: MAX_TOKENS, system: systemArg, messages, ...(tools.length ? { tools } : {}), ...(think ? THINK : {}) };
  const resp: any = await client.messages.create(params).catch((e: unknown) => {
    throw explain(e);
  });
  USAGE.in += resp.usage.input_tokens;
  USAGE.out += resp.usage.output_tokens;
  messages.push({ role: "assistant", content: resp.content });
  return {
    text: resp.content.filter((b: any) => b.type === "text").map((b: any) => b.text).join(""),
    calls: resp.content.filter((b: any) => b.type === "tool_use").map((b: any) => ({ id: b.id, name: b.name, args: b.input })),
    paused: resp.stop_reason === "pause_turn", // a server-side tool (web search) needs another pass
  };
}

function addResults(messages: any[], calls: Call[], outputs: string[]) {
  messages.push({ role: "user", content: calls.map((c, i) => ({ type: "tool_result", tool_use_id: c.id, content: outputs[i] })) });
}

/** One plain model call with no tools. Used for planning, critique and voting. */
async function llm(system: string, prompt: string): Promise<string> {
  return (await chat(system, [{ role: "user", content: prompt }])).text;
}

function parseJson(text: string): any {
  const spans = [["[", "]"], ["{", "}"]]
    .map(([open, close]) => ({ start: text.indexOf(open), close }))
    .filter((s) => s.start >= 0)
    .sort((a, b) => a.start - b.start);
  for (const { start, close } of spans) {
    try {
      return JSON.parse(text.slice(start, text.lastIndexOf(close) + 1));
    } catch {
      /* try the next candidate */
    }
  }
  throw new Error("no JSON found in: " + text.slice(0, 200));
}

async function callTool(name: string, args: any): Promise<string> {
  const fn = IMPLS[name];
  if (!fn) return "error: unknown tool " + name;
  const risky = RISKY.has(name);
  if (APPROVAL === "all" || (APPROVAL === "risky" && risky)) {
    const answer = await ask("\n  approve " + name + "(" + JSON.stringify(args).slice(0, 200) + ")? [y/N] ");
    if (answer.trim().toLowerCase() !== "y") return "error: the user declined this action";
  }
  try {
    return String(await fn(args));
  } catch (e: any) {
    return "error: " + e.message; // tool errors go back to the model so it can adjust
  }
}

// ---- OBSERVE ----------------------------------------------------------------------
/** Decide what the model gets to see after a tool runs. */
async function observe(name: string, text: string, task: string): Promise<string> {
  OBS_LOG.push("[" + name + "] " + text.slice(0, 4000));
  return text.slice(0, OBS_LIMIT);
}

// ---- the loop: REASON -> ACT -> OBSERVE -> DECIDE whether to go round again ---------
async function agentLoop(task: string, system = SYSTEM, history: any[] = [], tools: any[] = TOOLS): Promise<string> {
  history.push({ role: "user", content: task });
  for (let turn = 1; turn <= MAX_TURNS; turn++) {
    if (usedTokens() > TOKEN_BUDGET) return "[stopped: token budget reached]";
    const reply = await chat(system, history, tools, true); // REASON
    if (reply.text.trim()) {
      console.log("[reason " + turn + "] " + reply.text.trim().slice(0, 300));
      trace("reason", { turn, text: reply.text.trim().slice(0, 2000) });
    }
    if (reply.paused) continue;
    const calls = reply.calls;
    if (!calls.length) return reply.text; // DECIDE: no more actions requested, so the model is done
    const done = calls.find((c) => c.name === "finish");
    if (done) {
      FINISHED.flag = true;
      FINISHED.summary = done.args.summary ?? "";
      return FINISHED.summary;
    }

    const runCall = async (c: Call): Promise<string> => {
      console.log("[act " + turn + "] " + c.name + "(" + JSON.stringify(c.args).slice(0, 120) + ")"); // ACT
      trace("act", { turn, tool: c.name, input: c.args });
      const raw = await callTool(c.name, c.args);
      const seen = await observe(c.name, raw, task); // OBSERVE
      trace("observe", { turn, tool: c.name, chars: raw.length, shown: seen.length });
      return seen;
    };

    const outputs: string[] = [];
    for (const c of calls) outputs.push(await runCall(c));
    addResults(history, calls, outputs); // results go back in for the next REASON step
  }
  return "[stopped: MAX_TURNS reached]";
}


/** REASON -> ACT -> OBSERVE for one agent: shape the thinking, then run the tool loop. */
async function thinkAndAct(task: string, system = SYSTEM, history?: any[]): Promise<string> {
  let out = await agentLoop(task, system + REASON_RULES, history);
  return out;
}


// ---- shape: how the loop is wired into agents --------------------------------------
const STEPS = [
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
] as { name: string; instruction: string; gate?: string }[];

/** A fixed sequence: each step's output is the next step's input, with optional gates. */
async function topology(task: string): Promise<string> {
  let data = task;
  for (const [i, s] of STEPS.entries()) {
    console.log("\n[step " + (i + 1) + "/" + STEPS.length + "] " + s.name);
    data = await thinkAndAct(s.instruction + "\n\nInput:\n" + data);
    if (s.gate) {
      const verdict = await llm("You are a strict validator.", "Check: " + s.gate + "\n\nOutput:\n" + data + "\n\nReply 'PASS' or 'FAIL: reason'.");
      if (verdict.trim().toUpperCase().startsWith("FAIL")) return "[chain stopped at '" + s.name + "'] " + verdict;
    }
  }
  return data;
}


async function run(task: string): Promise<string> {
  return topology(task);
}

/** Used by server.ts. A server has no terminal to ask in, so it controls approval and clears state per request. */
const control = {
  tools: TOOLS,
  topology,
  setApproval(a: typeof APPROVAL) {
    APPROVAL = a;
  },
  /** Remove tools that can act (write files, run code, MCP servers) so an unattended server cannot misuse them. */
  async dropRisky() {
    const risky = new Set<string>(RISKY);
    TOOLS.splice(0, TOOLS.length, ...TOOLS.filter((t) => !risky.has(t.name)));
    for (const name of risky) delete IMPLS[name];
  },
  reset() {
    USAGE.in = 0;
    USAGE.out = 0;
    FINISHED.flag = false;
    FINISHED.summary = "";
    OBS_LOG.length = 0;
  },
};

export { run, usedTokens, control };

if ((process.argv[1] ?? "").endsWith("agent.ts")) {
  const task = process.argv.slice(2).join(" ") || "Notes: we agreed to ship v2 on the 14th. Priya owns the migration. Tom to confirm pricing by Friday.";
  run(task)
    .then((out) => {
      console.log("\n" + out);
      console.log("\n[tokens used: " + usedTokens() + "]");
    })
    .catch((e) => {
      console.error(e);
      process.exitCode = 1;
    });
}
