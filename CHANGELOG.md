# Changelog

Looprig uses semantic versions: a new major number for breaking changes to blueprints, a minor number for new features, a patch number for fixes.

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
