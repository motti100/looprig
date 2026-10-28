# Looprig v1.7.1

Build any AI agent from four moves: Reason, Act, Observe, Decide. Pick a technique (ReAct, chain or tree of thought, self-consistency, agentic RAG, Reflexion, routers, supervisor teams, goal loops) or tune each move, then copy working Python or TypeScript.

Works with OpenAI, Gemini, Claude, Groq, Mistral, DeepSeek, xAI, Together, OpenRouter, Ollama, LM Studio and any OpenAI-compatible endpoint.

## Use it

Open `index.html` in a browser. It is one file with no build step, no server and no third-party requests.

## Examples

Each folder has a `py` and a `ts` bundle: agent, evals, smoke test, deploy kit and blueprint.

- [`react-research-brief`](examples/react-research-brief): Research brief with ReAct: web search, short Thought lines, a sourced answer.
- [`rag-support-answers`](examples/rag-support-answers): Support answers from your own documents, with a grounding check on every claim.
- [`coder-data-analyst`](examples/coder-data-analyst): Data analyst that writes and runs Python, with an evaluator pass on the answer.
- [`evalopt-code-reviewer`](examples/evalopt-code-reviewer): Code reviewer that scores its own findings against a rubric and improves them.
- [`chain-meeting-follow-up`](examples/chain-meeting-follow-up): Meeting follow-up as a prompt chain with a gate between steps.
- [`goal-research-brief`](examples/goal-research-brief): Autonomous goal loop that keeps notes in progress.md and stops on finish.

## Deploy

Put `index.html` on any static host (Cloudflare Pages, GitHub Pages, Netlify). For GitHub Pages: push this folder, then Settings > Pages > deploy from the main branch.

## Notes

Generated code is a starting point. Read it before giving an agent tools that write, run code or reach the web. Model names change; pick "Other" in the model list to type a new id.

## When something goes wrong

Every generated agent has a built-in checkup: `python agent.py --doctor` (or `npx tsx agent.ts --doctor`) tests your key, the model and a tool call one step at a time. Add `--debug` to any run to watch each model call. Errors name the provider, the model, what the provider said and the next step. The Help tab in the app, and `TROUBLESHOOTING.md` in every bundle, list the common errors and fixes.

MIT licensed.
