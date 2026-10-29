# Changelog

Looprig uses semantic versions: a new major number for breaking changes to blueprints, a minor number for new features, a patch number for fixes.

## 2.1.1 (2026-10-29)
- PayPal donate link (paypal.me/motti10) on the home screen and in Learn; adds .github/FUNDING.yml

## 2.1.0 (2026-10-29)
- Support links: optional PayPal, GitHub Sponsors, Ko-fi, Buy Me a Coffee and Patreon links on the home screen and in Learn, set in one file (donate.json). Plain links only, no third-party scripts. A GitHub Sponsor button file is generated when configured.

## 2.0.3 (2026-10-29)
- The version number is shown on the home screen and in Learn again, not only in the builder

## 2.0.2 (2026-10-29)
- Learn shows clear feedback while a quest runs: a Working banner with a spinner, the current step and elapsed seconds, a Sent to model line, and a hint to press Stop if the provider is slow

## 2.0.1 (2026-10-29)
- API keys no longer disappear between quests: a key is kept for the tab (sessionStorage), shared by Learn and Build, and survives reloads. Closing the tab forgets it. Opt-in Remember on this device, plus Forget my keys.

## 2.0.0 (2026-10-29)
- Learn door: a home screen with Learn and Build, and a guided path of 17 quests in four worlds (Talk, Tools, The Loop, Ground and Remember). Each quest has a predict step, a no-key demo, a break-it option and an automatic check. Worlds unlock in order or by taking the boss challenge. The old quest panel is replaced by Learn.
- Now released into the public domain (the Unlicense).

## 1.13.2 (2026-10-29)
- Agents that reply with nothing are nudged to continue (up to twice) instead of silently ending the turn, and the Playground log now shows what the model said or that its reply was empty

## 1.13.1 (2026-10-29)
- Preview has a Maximize button (Esc or Exit maximize to leave) and a taller default size

## 1.13.0 (2026-10-29)
- Keep improving a project: describe a change and Refine edits the files you already have, with quick suggestions
- The project is remembered on this device across reloads; attaching an existing file makes it a project; Clear project and Restore the previous files

## 1.12.5 (2026-10-29)
- Goal loop now asks for real file changes each round, nudges after an idle round, and stops with a clear message after three idle rounds (browser, Python and TypeScript)
- Tip shown when a small model is picked for a project-building agent

## 1.12.4 (2026-10-29)
- Playground errors now say where it broke: no connection at all, a blocked response (usually a browser extension or VPN), or a request the provider refused

## 1.12.3 (2026-10-29)
- Playground: tool schemas no longer send an empty required list (Gemini rejects it, which showed as a network error); when a call fails in the browser, a small test request now tells unreachable apart from refused

## 1.12.2 (2026-10-29)
- Quests can be ticked by hand: click the circle, or use Mark as done in the lesson panel

## 1.12.1 (2026-10-29)
- Quests in the list are clickable: pick any quest to read its lesson and jump to it

## 1.12.0 (2026-10-29)
- Simple mode is now the default: pick a plain-language starter, try it, get code. Advanced keeps every control
- New short, readable agent (about a hundred lines on the official Claude and OpenAI SDKs), tested against the real SDKs, in Python and TypeScript
- Watch a demo: a scripted run of the real loop, tools and preview, so no API key is needed to see an agent work
- Optional Learn with quests (Simple mode only): seven quests, progress saved on your device
- Next steps tab and NEXT_STEPS.md; a test that the browser Playground and the generated code make the same model calls for every technique

## 1.11.0 (2026-10-28)
- Playground runs every technique: tree of thoughts, plan, self-consistency, grounding, reflexion, evaluator, human review, router, chain, parallel, orchestrator, supervisor team, goal loop and chat
- New preview_html tool: pages and games the agent writes load in a sandboxed preview that reports JavaScript errors, drawing and key response back to the agent
- Playground adds search_docs, memory, optional Tavily web search for non-Claude models, and a Preview button on html files

## 1.10.0 (2026-10-28)
- New four-step layout: Describe, Choose how it thinks, Try it, Fine-tune and get code. Technique cards with plain descriptions, a floating header with step links, softer surfaces and a clearer light and dark look.
- Project builder technique: list_dir, edit_file (exact edits) and run_shell (allowlisted commands such as pytest and npm test) in Python and TypeScript agents, with a plan, build, test, fix loop.
- Playground runs project tasks in the browser: an in-memory project folder, a JavaScript sandbox (run_js) with a 10 second limit and no network, a files viewer and a zip download.
- write_file now creates folders; path checks no longer allow sibling-folder prefixes.

## 1.9.1 (2026-10-28)
- Playground: the agent is now told only about the tools the browser really offers, so it no longer tries write_file or run_python and fails. Unknown tool calls get a reply that lists what is available.

## 1.9.0 (2026-10-28)
- Attachments. In the Playground, attach files and images with a button, drag and drop, or paste; large pictures are resized for you.
- Generated agents accept --file (text, code, CSV, JSON; PDF on Claude) and --image (png, jpg, gif, webp) in Python and TypeScript.
- Help and README explain attachments and the errors you may see.

## 1.8.0 (2026-10-28)
- Playground: run your agent from the page with your own key. The Reason, Act, Observe and Decide boxes light up as it works, each step streams into a console, and you can answer the agent's questions inline.
- Run history with a side-by-side difference (tokens, tool calls, time), and send any run to the Trace tab.
- The Test task field is shared between the builder and the Playground. Hosted copy only: the in-page preview blocks network calls.

## 1.7.1 (2026-10-28)
- Clear message when a Python package is missing (wrong Python or a virtual environment that was moved or renamed), with the exact fix.
- Gemini, Groq and other compatible providers now say they use their own OpenAI-compatible API and need no OpenAI account.
- Troubleshooting guide covers broken virtual environments.

## 1.7.0 (2026-10-28)
- Renamed from Loopsmith to Looprig. Saved agents, theme and blueprints made under the old name still load.
- Example bundles, README and the download folder use the new name.

## 1.6.0 (2026-10-28)
- Version number shown in the app, in every generated file, in blueprints and in the README.
- Changelog in the app and in the download. `node bump.js` raises the version and records the change.

## 1.5.0 (2026-10-28)
- Every generated agent has `--doctor` (checks key, model and a tool-call round trip) and `--debug` (prints each model call).
- Errors now show the provider's reply and a plain next step.
- New Help tab and `TROUBLESHOOTING.md` in every bundle.

## 1.4.1 (2026-10-28)
- Fixed Gemini 3 tool calls failing with a 400: the thought signature is now passed back.
- Gemini model list refreshed; the default is `gemini-flash-latest`.

## 1.4.0 (2026-10-27)
- Missing-key check, clearer model-call errors, `--list` for the smoke test.

## 1.3.0 (2026-10-27)
- MCP tools, structured output with schema check, deploy kit (API server, Docker), smoke test, LangGraph and OpenAI Agents SDK exports, ready-made examples.

## 1.2.0 (2026-10-26)
- Standalone build with share links, saved agents, undo and redo, cost estimate, trace replay and baseline compare.

## 1.1.0 (2026-10-26)
- Providers beyond Claude: OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI, Together, OpenRouter, Ollama, LM Studio and any OpenAI-compatible endpoint.

## 1.0.0 (2026-10-26)
- First release: the Reason, Act, Observe, Decide loop, 19 presets and Python and TypeScript generators.
