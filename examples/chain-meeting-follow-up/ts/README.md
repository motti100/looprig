# Chain Meeting Follow Up

Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain

Built with [Loopsmith](.). Provider: Anthropic (Claude), model `claude-sonnet-5-5`.

## Run it

```
npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
export ANTHROPIC_API_KEY="..."
npx tsx agent.ts "Notes: we agreed to ship v2 on the 14th. Priya owns the migration. Tom to confirm pricing by Friday."
```

## What is in this folder

- `agent.ts`: the agent. Settings are at the top of the file.
- `evals.ts`: a small regression suite. Add cases as you find failures.
- `smoke_test.py`: checks that your provider keys can do tool calling.
- `blueprint.json`: load it back into Loopsmith to change the design.
- `server.ts`, `Dockerfile`, `.env.example`, `package.json`: run it as an HTTP service.

## Before you rely on it

- Read the code. Tools that write files, run code or reach the web deserve a careful look.
- Keep approval on while you learn how the agent behaves. A server runs with approval off and risky tools removed unless you set `ALLOW_RISKY_TOOLS=1`.
- Hard limits (turns, tokens) are constants near the top of the agent. Lower them while testing.
- Model names change. If a provider retires one, edit `MODEL`.
