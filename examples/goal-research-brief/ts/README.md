# Goal Research Brief

Reason: plan first | Act: read_file, write_file, run_python | Observe: log | Decide: stop when done | Shape: goal mode

Built with [Looprig](.) v1.13.1. Provider: Anthropic (Claude), model `claude-sonnet-5-5`.

## Run it

```
npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
export ANTHROPIC_API_KEY="..."
npx tsx agent.ts "What are the main trade-offs between SQLite and Postgres for a small SaaS product?"
```

Give it files or pictures: `npx tsx agent.ts "your task" --file notes.txt --image photo.png`

## What is in this folder

- `agent.ts`: the agent. Settings are at the top of the file.
- `evals.ts`: a small regression suite. Add cases as you find failures.
- `smoke_test.py`: checks that your provider keys can do tool calling.
- `TROUBLESHOOTING.md`: what each error means and how to fix it. Start with `npx tsx agent.ts --doctor`.
- `blueprint.json`: load it back into Looprig to change the design.
- `server.ts`, `Dockerfile`, `.env.example`, `package.json`: run it as an HTTP service.

## Before you rely on it

- Read the code. Tools that write files, run code or reach the web deserve a careful look.
- Keep approval on while you learn how the agent behaves. A server runs with approval off and risky tools removed unless you set `ALLOW_RISKY_TOOLS=1`.
- Hard limits (turns, tokens) are constants near the top of the agent. Lower them while testing.
- Model names change. If a provider retires one, edit `MODEL`.
