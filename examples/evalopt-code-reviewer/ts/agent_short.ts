/*evalopt-code-reviewer: the short version.

What it does: Review a code file for bugs, security issues and unclear naming. Report findings ranked by severity with suggested fixes..

The loop has four moves, marked in the code:
  REASON   the model reads the conversation and decides what to do
  ACT      it asks to use a tool
  OBSERVE  we run the tool and give the result back
  DECIDE   if it asks for nothing more, it is done

Left out of this short version: the evaluator. The full agent has them.

Run it:
    npm install @anthropic-ai/sdk tsx
    export ANTHROPIC_API_KEY=...
    npx tsx agent_short.ts "Review app.py and list the three most serious problems."
*/
import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-sonnet-5-5";
const MAX_TURNS = 10; // a hard stop, so a confused agent cannot run forever
const SYSTEM = `You are Evalopt Code Reviewer, an AI agent.

Goal: Review a code file for bugs, security issues and unclear naming. Report findings ranked by severity with suggested fixes.

You work in a loop: decide what is needed, call a tool when it helps, read the result, and continue until you can answer. Tools: read_file. Use a tool only when it moves the task forward, and read each result before continuing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it.`;

// ---- TOOLS: a description the model reads, and a function we run
const TOOLS = [
  {"name":"read_file","description":"Read a text file from the working directory.","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}
] as unknown as Anthropic.Messages.ToolUnion[];

function safePath(p: string): string { // tools may only touch files inside this folder
  const full = path.resolve(p || ".");
  if (full !== process.cwd() && !full.startsWith(process.cwd() + path.sep)) throw new Error("outside the working folder");
  return full;
}

type Args = Record<string, string>;
const RUN: Record<string, (a: Args) => string | Promise<string>> = {
  read_file: ({ path: p }) => fs.readFileSync(safePath(p), "utf8").slice(0, 20000),
};

async function runTool(name: string, args: Args): Promise<string> {
  try { return String(await RUN[name](args)); }
  catch (e) { return `error: ${(e as Error).message}`; } // the model sees the error and can recover
}

// ---- THE LOOP
const task = process.argv[2] ?? "Review app.py and list the three most serious problems.";
const client = new Anthropic(); // reads ANTHROPIC_API_KEY
const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: task }];

let done = false;
for (let turn = 0; turn < MAX_TURNS && !done; turn++) {
  // REASON: the model reads everything so far and decides what to do
  const reply = await client.messages.create({ model: MODEL, max_tokens: 4096, system: SYSTEM, tools: TOOLS, messages });
  messages.push({ role: "assistant", content: reply.content });
  const calls = reply.content.filter((b): b is Anthropic.Messages.ToolUseBlock => b.type === "tool_use");

  // DECIDE: no tool requested means the model has its answer
  if (calls.length === 0) {
    console.log(reply.content.map((b) => (b.type === "text" ? b.text : "")).join(""));
    done = true;
    break;
  }

  const results: Anthropic.Messages.ToolResultBlockParam[] = [];
  for (const call of calls) {
    // ACT: run the tool the model asked for, then OBSERVE: keep the result for the next turn
    results.push({ type: "tool_result", tool_use_id: call.id, content: await runTool(call.name, call.input as Args) });
  }
  messages.push({ role: "user", content: results });
}
if (!done) console.log("Stopped: reached MAX_TURNS without a final answer.");
