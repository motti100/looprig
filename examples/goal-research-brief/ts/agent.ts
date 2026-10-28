/**
 * goal-research-brief
 * Reason: plan first | Act: read_file, write_file, run_python | Observe: log | Decide: stop when done | Shape: goal mode
 *
 * Built with Loopsmith. Run it:
 *   npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
 *   export ANTHROPIC_API_KEY=...
 *   npx tsx agent.ts "your task here"
 */
import Anthropic from "@anthropic-ai/sdk";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline/promises";
import { execFileSync } from "node:child_process";

// ---- settings (edit freely) ---------------------------------------------------
const PROVIDER = "anthropic";
const MODEL = "claude-sonnet-5-5";
const MAX_TOKENS = 4096; // per model call
const MAX_TURNS = 10; // tool-loop turns per pass through the loop
const TOKEN_BUDGET = 300000; // hard stop for the whole run
let APPROVAL = "risky" as "none" | "risky" | "all"; // ask before running tools
const RISKY = new Set(["write_file", "run_python", "my_custom_tool"]);
const OBS_LIMIT = 6000; // max characters of one tool result the model sees
const MAX_RETRIES = 5; // the SDK retries rate limits, 5xx errors and timeouts with backoff
const TIMEOUT_S = 120; // seconds to wait for one model call
const THINK: Record<string, unknown> = {}; // model-native extended thinking, if enabled
const TRACE_FILE = "trace.jsonl"; // one JSON line per reason / act / observe event

const client = new Anthropic({ maxRetries: MAX_RETRIES, timeout: TIMEOUT_S * 1000 }); // reads ANTHROPIC_API_KEY from the environment

const SYSTEM = `You are Goal Research Brief, an AI agent.

Goal: Research a topic on the web and write a short, sourced brief with key findings and open questions.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file, write_file, run_python. Use a tool only when it moves the task forward, and read each result before continuing.

You run in rounds. Your notes are saved in progress.md between rounds. Make real progress each round, and call finish only when the goal is fully met.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it.`;
const REASON_RULES = "";
const PLANNER = "You are a planner. Output a short numbered plan and nothing else.";
const LOG_FILE = "observations.log";

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
    },
    {
        "name": "write_file",
        "description": "Write text to a file in the working directory, replacing its contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string"
                },
                "content": {
                    "type": "string"
                }
            },
            "required": [
                "path",
                "content"
            ]
        }
    },
    {
        "name": "run_python",
        "description": "Run a short Python 3 script and return what it prints (stdout and stderr). Use print() to show results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string"
                }
            },
            "required": [
                "code"
            ]
        }
    },
    {
        "name": "finish",
        "description": "Call this only when the goal is fully met. Pass a summary of the outcome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string"
                }
            },
            "required": [
                "summary"
            ]
        }
    }
];

function safePath(p: string) {
  const full = path.resolve(p);
  if (!full.startsWith(process.cwd())) throw new Error("path is outside the working directory");
  return full;
}

function toolReadFile(a: any) {
  return fs.readFileSync(safePath(a.path), "utf8").slice(0, 20000);
}


function toolWriteFile(a: any) {
  const full = path.resolve(a.path);
  if (!full.startsWith(process.cwd())) throw new Error("path is outside the working directory");
  fs.writeFileSync(full, a.content);
  return "wrote " + String(a.content).length + " characters to " + a.path;
}


function toolRunPython(a: any) {
  // Runs on YOUR machine. Keep approval on, or move this into a sandbox/container.
  try {
    return execFileSync("python3", ["-c", a.code], { timeout: 30000, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).slice(-6000);
  } catch (e: any) {
    return String((e.stdout ?? "") + (e.stderr ?? "") || e.message).slice(-6000);
  }
}

const IMPLS: Record<string, (a: any) => any> = {
  read_file: toolReadFile,
  write_file: toolWriteFile,
  run_python: toolRunPython,
};


// ---- provider adapter: the only code that knows which API is underneath -------------
const USAGE = { in: 0, out: 0 };
const FINISHED = { flag: false, summary: "" };
const OBS_LOG: string[] = []; // raw tool results, kept as evidence

const usedTokens = () => USAGE.in + USAGE.out;

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
  const resp: any = await client.messages.create(params);
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
  fs.appendFileSync(LOG_FILE, "## " + name + "\n" + text + "\n\n");
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


// ---- REASON: plan first --------------------------------------------------------------
async function makePlan(task: string): Promise<string> {
  return llm(PLANNER, "Task: " + task + "\n\nWrite a 3-6 step plan. Say which tool each step needs, if any.");
}

/** REASON -> ACT -> OBSERVE for one agent: shape the thinking, then run the tool loop. */
async function thinkAndAct(task: string, system = SYSTEM, history?: any[]): Promise<string> {
  task += "\n\nPlan to follow:\n" + (await makePlan(task));
  let out = await agentLoop(task, system + REASON_RULES, history);
  return out;
}


// ---- shape: how the loop is wired into agents --------------------------------------
async function topology(task: string, history?: any[]): Promise<string> {
  return thinkAndAct(task, SYSTEM, history);
}


const PROGRESS = "progress.md";
const MAX_ITERATIONS = 8;

/** Goal loop: every iteration starts fresh and reads its notes from disk, until `finish` or a cap. */
async function run(task: string): Promise<string> {
  for (let i = 1; i <= MAX_ITERATIONS; i++) {
    const notes = fs.existsSync(PROGRESS) ? fs.readFileSync(PROGRESS, "utf8") : "(nothing yet)";
    const prompt =
      "GOAL:\n" + task + "\n\nPROGRESS NOTES:\n" + notes + "\n\n" +
      "Do the next most useful chunk of work. Rewrite " + PROGRESS + " with write_file, keeping earlier notes and adding what you just did. " +
      "Call finish with a summary only when the goal is fully met.";
    console.log("\n=== iteration " + i + "/" + MAX_ITERATIONS + " ===");
    await topology(prompt);
    if (FINISHED.flag) {
      return FINISHED.summary;
    }
    if (usedTokens() > TOKEN_BUDGET) return "[stopped: token budget reached]";
  }
  return "[stopped: iteration limit]";
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
  const task = process.argv.slice(2).join(" ") || "What are the main trade-offs between SQLite and Postgres for a small SaaS product?";
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
