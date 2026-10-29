# LoopRig v3.5.0

Build any AI agent from four moves: Reason, Act, Observe, Decide. Pick a technique (ReAct, chain or tree of thought, self-consistency, agentic RAG, Reflexion, routers, supervisor teams, goal loops) or tune each move, then copy working Python or TypeScript.

Works with Claude, OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI, Together, OpenRouter, Fireworks, NVIDIA, Hugging Face, Ollama, LM Studio and any OpenAI-compatible endpoint, including Azure OpenAI (choose Custom: base URL `https://YOUR-RESOURCE.openai.azure.com/openai/v1/`, and use your deployment name as the model).

## Two doors

**Learn** is a guided path of 37 short quests in nine worlds: a first model call, tools, the loop, grounding and memory, thinking techniques, workflows, teams, safety (approvals, budgets, prompt injection) and shipping real code. Every quest has a demo that needs no key, and a step-by-step animation of what the model and your code say to each other. **Build** is the full builder for people who already know their way around.

## The Lab

Compare models side by side, run evals, copy a run as a share link that replays in any browser (the steps travel in the link, nothing is uploaded), set up a local model with Ollama, browse example agents, earn badges and a self-issued certificate, and back up your progress (API keys are never included).

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

## Security

See `SECURITY.md`. In short: keys stay in your browser and go only to the provider you pick; the page loads no third-party code and ships a Content Security Policy; agents in the Playground work on a pretend folder and run code in a sandbox.

## When something goes wrong

Every generated agent has a built-in checkup: `python agent.py --doctor` (or `npx tsx agent.ts --doctor`) tests your key, the model and a tool call one step at a time. Add `--debug` to any run to watch each model call. The short version (`agent_short.py` or `agent_short.ts`) is the same loop on the official SDK in about a hundred lines, with each move labeled: read that one first. `NEXT_STEPS.md` says what to do after the first run. Give it files or pictures with `--file notes.txt` and `--image photo.png`, or drop them onto the Playground. The Project builder technique adds list, edit and run-command tools. In the Playground it works on an in-memory folder and runs JavaScript in a sandbox, and web pages and games it writes are loaded in a preview that reports their errors back so the agent can fix them. Every technique (plan, tree of thoughts, voting, reflexion, evaluator, routers, chains, teams, goal loops) runs in the Playground; only MCP servers, Python and shell need the generated code on your computer. Errors name the provider, the model, what the provider said and the next step. The Help tab in the app, and `TROUBLESHOOTING.md` in every bundle, list the common errors and fixes.

Public domain (the Unlicense): copy it, change it, sell it, no credit needed.
