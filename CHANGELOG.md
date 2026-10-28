# Changelog

Looprig uses semantic versions: a new major number for breaking changes to blueprints, a minor number for new features, a patch number for fixes.

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
