/*rag-support-answers: the short version.

What it does: Answer customer questions using our help documents, and flag anything that needs a human..

The loop has four moves, marked in the code:
  REASON   the model reads the conversation and decides what to do
  ACT      it asks to use a tool
  OBSERVE  we run the tool and give the result back
  DECIDE   if it asks for nothing more, it is done

Left out of this short version: searching your documents, the grounding check, result compression and logging. The full agent has them.

Run it:
    npm install @anthropic-ai/sdk tsx
    export ANTHROPIC_API_KEY=...
    npx tsx agent_short.ts "A customer asks how to change the email address on their account."
*/
import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-sonnet-5-5";
const MAX_TURNS = 10; // a hard stop, so a confused agent cannot run forever
const SYSTEM = `You are Rag Support Answers, an AI agent.

Goal: Answer customer questions using our help documents, and flag anything that needs a human.

Answer from your own knowledge and reasoning. If you are missing information, say what is missing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it.`;

// ---- TOOLS: a description the model reads, and a function we run
const TOOLS = [

] as unknown as Anthropic.Messages.ToolUnion[];

type Args = Record<string, string>;
const RUN: Record<string, (a: Args) => string | Promise<string>> = {
};

async function runTool(name: string, args: Args): Promise<string> {
  try { return String(await RUN[name](args)); }
  catch (e) { return `error: ${(e as Error).message}`; } // the model sees the error and can recover
}

// ---- THE LOOP
const task = process.argv[2] ?? "A customer asks how to change the email address on their account.";
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
