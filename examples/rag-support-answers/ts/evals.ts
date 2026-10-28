// Smoke tests for rag-support-answers. Edit CASES, then run:  npx tsx evals.ts

import { run, usedTokens } from "./agent";

const CASES = [
  {
    task: "A customer asks how to change the email address on their account.",
    mustContain: [] as string[], // strings the answer has to include
    mustNotContain: [] as string[], // strings that signal a failure
    maxTokens: 100000,
  },
];

async function main() {
  let failed = 0;
  for (const [i, c] of CASES.entries()) {
    const before = usedTokens();
    const answer = await run(c.task);
    const low = answer.toLowerCase();
    const missing = c.mustContain.filter((s) => !low.includes(s.toLowerCase()));
    const banned = c.mustNotContain.filter((s) => low.includes(s.toLowerCase()));
    const spent = usedTokens() - before;
    const ok = !missing.length && !banned.length && spent <= c.maxTokens && !answer.startsWith("[stopped");
    console.log((ok ? "PASS" : "FAIL") + " case " + (i + 1) + ": " + c.task.slice(0, 60) + "  (" + spent + " tokens)");
    if (!ok) {
      failed++;
      console.log("   missing:", missing, "banned found:", banned);
    }
  }
  process.exit(failed ? 1 : 0);
}

main();
