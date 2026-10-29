/**
 * evalopt-code-reviewer
 * Reason: direct | Act: read_file | Observe: raw | Decide: evaluate >= 8 | Shape: single agent
 *
 * Built with LoopRig v3.6.5. Run it:
 *   npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
 *   export ANTHROPIC_API_KEY=...
 *   npx tsx agent.ts "your task here"
 */
import Anthropic from "@anthropic-ai/sdk";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline/promises";

// ---- settings (edit freely) ---------------------------------------------------
const PROVIDER = "anthropic";
const MODEL = "claude-sonnet-5-5";
const MAX_TOKENS = 4096; // per model call
const MAX_TURNS = 10; // tool-loop turns per pass through the loop
const TOKEN_BUDGET = 200000; // hard stop for the whole run
let APPROVAL = "risky" as "none" | "risky" | "all"; // ask before running tools
const RISKY = new Set(["write_file", "edit_file", "run_python", "run_shell", "my_custom_tool"]);
const OBS_LIMIT = 6000; // max characters of one tool result the model sees
const MAX_RETRIES = 5; // the SDK retries rate limits, 5xx errors and timeouts with backoff
const TIMEOUT_S = 120; // seconds to wait for one model call
const THINK: Record<string, unknown> = {}; // model-native extended thinking, if enabled
const TRACE_FILE = "trace.jsonl"; // one JSON line per reason / act / observe event

const client = new Anthropic({ maxRetries: MAX_RETRIES, timeout: TIMEOUT_S * 1000 }); // reads ANTHROPIC_API_KEY from the environment

const SYSTEM = `You are Evalopt Code Reviewer, an AI agent.

Goal: Review a code file for bugs, security issues and unclear naming. Report findings ranked by severity with suggested fixes.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file. Use a tool only when it moves the task forward, and read each result before continuing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it.`;
const REASON_RULES = "";
const EVALUATOR = "You are a strict evaluator. Score the attempt against the rubric.";
const RUBRIC = "Accurate, complete, clear, and follows the goal. No unsupported claims.";
const EVAL_ROUNDS = 3;
const THRESHOLD = 8; // stop once the score reaches this (1-10)

// ---- ACT: tools ---------------------------------------------------------------
const TOOLS: any[] = [
    {
        "name": "read_file",
        "description": "Read a text file from the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string"
                }
            },
            "required": [
                "path"
            ]
        }
    }
];

function safePath(p: string) {
  const full = path.resolve(p);
  const cwd = process.cwd();
  if (full !== cwd && !full.startsWith(cwd + path.sep)) throw new Error("path is outside the working directory");
  return full;
}

function toolReadFile(a: any) {
  return fs.readFileSync(safePath(a.path), "utf8").slice(0, 20000);
}

const IMPLS: Record<string, (a: any) => any> = {
  read_file: toolReadFile,
};


// ---- provider adapter: the only code that knows which API is underneath -------------
const USAGE = { in: 0, out: 0 };
const FINISHED = { flag: false, summary: "" };
const OBS_LOG: string[] = []; // raw tool results, kept as evidence

const usedTokens = () => USAGE.in + USAGE.out;

const KEY_NAME = "ANTHROPIC_API_KEY";
const DEBUG = process.argv.includes("--debug") || !!process.env.AGENT_DEBUG; // npx tsx agent.ts --debug "task"

// ---- attachments: npx tsx agent.ts "your task" --file notes.txt --image photo.png ----
// Text files are pasted into the task. Images (and PDFs, where the provider reads them) go in as real attachments.
const ATTACH: { kind: "image" | "pdf"; mime: string; b64: string }[] = [];
const FILE_LIMIT = 60000; // characters of a text file kept in the prompt
const IMG_TYPES: Record<string, string> = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", gif: "image/gif", webp: "image/webp" };

function failNow(msg: string): never {
  console.error("ERROR: " + msg);
  process.exit(1);
}

/** Split argv into the task words and text-file blocks. Images are collected in ATTACH. */
function loadAttachments(argv: string[]): { task: string; texts: string[] } {
  const words: string[] = [];
  const texts: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--debug") continue;
    if (a !== "--file" && a !== "--image") {
      words.push(a);
      continue;
    }
    const p = argv[++i];
    if (!p) failNow(`${a} needs a path, like: ${a} notes.txt`);
    if (!fs.existsSync(p) || !fs.statSync(p).isFile()) failNow(`cannot find ${p} (looking in ${process.cwd()}). Check the path and run again.`);
    const name = p.split(/[\\/]/).pop() as string;
    const ext = name.includes(".") ? (name.split(".").pop() as string).toLowerCase() : "";
    const data = fs.readFileSync(p);
    if (a === "--image" || IMG_TYPES[ext]) {
      if (!IMG_TYPES[ext]) failNow(`${name} is not an image type I can send (use png, jpg, gif or webp).`);
      if (data.length > 15_000_000) failNow(`${name} is over 15 MB. Make it smaller and try again.`);
      ATTACH.push({ kind: "image", mime: IMG_TYPES[ext], b64: data.toString("base64") });
    } else if (ext === "pdf") {
      ATTACH.push({ kind: "pdf", mime: "application/pdf", b64: data.toString("base64") });
    } else {
      const text = data.toString("utf8");
      if (text.slice(0, 2000).includes("\u0000")) failNow(`${name} looks like a binary file. --file reads text; use --image for pictures.`);
      const note = text.length > FILE_LIMIT ? `\n[truncated: only the first ${FILE_LIMIT} characters are included]` : "";
      texts.push(`--- file: ${name} ---\n${text.slice(0, FILE_LIMIT)}${note}\n--- end of ${name} ---`);
    }
  }
  return { task: words.join(" "), texts };
}

/** The first user message: plain text, or the attachments followed by the text. */
function userContent(text: string): any {
  if (!ATTACH.length) return text;
  const blocks: any[] = ATTACH.map((a) => {
    return { type: a.kind === "image" ? "image" : "document", source: { type: "base64", media_type: a.mime, data: a.b64 } };
  });
  return [...blocks, { type: "text", text }];
}

/** Turn a provider error into one plain-English next step. */
function hint(e: any): string {
  const code = e?.status ?? e?.response?.status;
  const text = String(e?.message ?? e).toLowerCase();
  if (code === 401 || code === 403 || text.includes("api key")) return "The provider rejected your key. Check that " + KEY_NAME + " holds a real, active key and was exported in THIS terminal. Run: npx tsx agent.ts --doctor";
  if (code === 404 || text.includes("no longer available")) return "The provider does not know the model '" + MODEL + "' (renamed, retired or not on your plan). Edit MODEL at the top of this file. Run: npx tsx agent.ts --doctor";
  if (code === 429 || text.includes("quota")) return "Rate limit or quota hit. Wait a minute, lower MAX_TURNS, or check your plan and billing.";
  if ([500, 502, 503, 504].includes(code) || text.includes("timed out") || text.includes("connection")) return "The provider is busy, slow or unreachable. It is usually temporary: try again, or switch MODEL to a lighter one.";
  if (code === 400) return "The provider refused the request itself. The text above says which field. Run with --debug, or run --doctor to test the model on its own.";
  return "Run: npx tsx agent.ts --doctor  (tests your key, model and tool calling one step at a time)";
}

/** Say what was being called and what to do next, so a bare error is never a mystery. */
function explain(e: any): Error {
  let body = "";
  try {
    body = JSON.stringify(e?.error ?? "").slice(0, 600);
  } catch {
    /* ignore */
  }
  return new Error("model call failed: " + (e?.message ?? e) + "\n  provider=" + PROVIDER + " model=" + MODEL + "\n  provider said: " + (body || "(nothing)") + "\n  next step: " + hint(e));
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

type Call = { id: string; name: string; args: any; extra?: any };
type Reply = { text: string; calls: Call[]; paused: boolean };

/** One model call. Appends the assistant turn to `messages` and returns a neutral reply. */
async function rawChat(system: string, messages: any[], tools: any[] = [], think = false): Promise<Reply> {
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
  history.push({ role: "user", content: userContent(task) });
  let empties = 0;
  for (let turn = 1; turn <= MAX_TURNS; turn++) {
    if (usedTokens() > TOKEN_BUDGET) return "[stopped: token budget reached]";
    const reply = await chat(system, history, tools, true); // REASON
    if (reply.text.trim()) {
      console.log("[reason " + turn + "] " + reply.text.trim().slice(0, 300));
      trace("reason", { turn, text: reply.text.trim().slice(0, 2000) });
    }
    if (reply.paused) continue;
    const calls = reply.calls;
    if (!calls.length) { // DECIDE: no more actions requested, so the model is done
      if (!reply.text.trim() && empties < 2) { // saying nothing at all means stuck, not finished
        empties++;
        console.log("[reason " + turn + "] (empty reply, asking the model to continue)");
        history.pop();
        history.push({ role: "user", content: "You replied with nothing. Continue: call a tool, or give your final answer." });
        continue;
      }
      return reply.text;
    }
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

    let outputs: string[];
    if (calls.length > 1 && APPROVAL === "none") {
      outputs = await Promise.all(calls.map(runCall)); // independent calls in one turn run at the same time
    } else {
      outputs = [];
      for (const c of calls) outputs.push(await runCall(c));
    }
    addResults(history, calls, outputs); // results go back in for the next REASON step
  }
  return "[stopped: MAX_TURNS reached]";
}

async function chat(system: string, messages: any[], tools: any[] = [], think = false): Promise<Reply> {
  if (DEBUG) console.log("[debug] -> " + PROVIDER + "/" + MODEL + " messages=" + messages.length + " tools=" + JSON.stringify(tools.map((t) => t.name)));
  const out = await rawChat(system, messages, tools, think);
  if (DEBUG) console.log("[debug] <- text=" + out.text.length + " chars, tool calls=" + JSON.stringify(out.calls.map((c) => c.name)) + ", tokens so far=" + usedTokens());
  return out;
}

/** npx tsx agent.ts --doctor : test the key, the model and a tool-call round trip, one step at a time. */
async function doctor(): Promise<number> {
  console.log("provider : " + PROVIDER + "\nmodel    : " + MODEL);
  const key = process.env[KEY_NAME] ?? "";
  console.log("key      : " + KEY_NAME + " = " + (key.length > 8 ? key.slice(0, 4) + "..." + key.slice(-2) + " (" + key.length + " chars)" : key ? "(too short to be a real key)" : "NOT SET"));
  const echo = [{ name: "echo", description: "Echo text back.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"] } }];
  try {
    const r = await rawChat("Reply briefly.", [{ role: "user", content: "Say hi." }]);
    console.log("[ok]   1. plain call works: " + JSON.stringify(r.text.trim().slice(0, 60)));
  } catch (e) {
    console.log("[FAIL] 1. plain call: " + (e as Error).message);
    return 1;
  }
  try {
    const msgs: any[] = [{ role: "user", content: "Call the echo tool with text 'ping', then say done." }];
    let r = await rawChat("Use the tools you are given.", msgs, echo);
    if (!r.calls.length) {
      console.log("[warn] 2. this model did not call the tool. The agent may struggle: try a stronger MODEL.");
      return 0;
    }
    addResults(msgs, r.calls, ["pong"]);
    r = await rawChat("Use the tools you are given.", msgs, echo);
    console.log("[ok]   2. tool call and follow-up work. Your agent should run.");
  } catch (e) {
    console.log("[FAIL] 2. tool-call round trip: " + (e as Error).message);
    return 1;
  }
  return 0;
}


/** REASON -> ACT -> OBSERVE for one agent: shape the thinking, then run the tool loop. */
async function thinkAndAct(task: string, system = SYSTEM, history?: any[]): Promise<string> {
  let out = await agentLoop(task, system + REASON_RULES, history);
  return out;
}


// ---- shape: how the loop is wired into agents --------------------------------------
async function topology(task: string, history?: any[]): Promise<string> {
  return thinkAndAct(task, SYSTEM, history);
}


// ---- DECIDE: is this good enough to return? --------------------------------------
/** A separate evaluator scores each attempt against the rubric; keep the best. */
async function evaluate(task: string, draft: string): Promise<string> {
  let best = draft, bestScore = -1, attempt = draft;
  for (let r = 1; r <= EVAL_ROUNDS; r++) {
    const ask = "Task: " + task + "\n\nAttempt:\n" + attempt + "\n\nRubric:\n" + RUBRIC;
    const verdict = parseJson(await llm(EVALUATOR, ask + '\n\nReturn ONLY JSON: {"score": <1-10>, "feedback": "<what to fix>"}'));
    console.log("  [evaluate " + r + "] score " + verdict.score + ": " + String(verdict.feedback).slice(0, 160));
    if (verdict.score > bestScore) {
      best = attempt;
      bestScore = verdict.score;
    }
    if (verdict.score >= THRESHOLD || r === EVAL_ROUNDS) break;
    attempt = await thinkAndAct("Task: " + task + "\n\nPrevious attempt:\n" + attempt + "\n\nEvaluator feedback:\n" + verdict.feedback + "\n\nImprove it.");
  }
  return best;
}

async function improve(task: string, draft: string): Promise<string> {
  draft = await evaluate(task, draft);
  return draft;
}


async function run(task: string): Promise<string> {
  return improve(task, await topology(task));
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
  if (process.argv.includes("--doctor")) {
    doctor().then((code) => process.exit(code));
  } else {
    const parsed = loadAttachments(process.argv.slice(2));
    let task = parsed.task || "Review app.py and list the three most serious problems.";
    if (parsed.texts.length) task += "\n\n" + parsed.texts.join("\n\n");
    run(task)
      .then((out) => {
        console.log("\n" + out);
        console.log("\n[tokens used: " + usedTokens() + "]");
      })
      .catch((e) => {
        if (DEBUG) console.error(e);
        else console.error("\nERROR: " + (e?.message ?? e));
        process.exitCode = 1;
      });
  }
}
