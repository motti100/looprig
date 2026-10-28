# Troubleshooting: Anthropic (Claude)

## Start here: run the doctor

```
export ANTHROPIC_API_KEY="your-key"
npx tsx agent.ts --doctor
```

It checks, one step at a time: (1) your key is set, (2) the model answers a plain question, (3) the model can call a tool and accept the result. The first step that fails tells you what to fix. If all three pass, the agent itself is fine.

For a failing real run, add `--debug` to print every model call and what came back:

```
npx tsx agent.ts --debug "your task"
```

## Give it a file or an image

```
npx tsx agent.ts "Review this code" --file app.py
npx tsx agent.ts "What is wrong in this screenshot?" --image error.png
npx tsx agent.ts "Summarize" --file notes.txt --file data.csv --image chart.png
```

`--file` pastes a text file (code, notes, CSV, JSON; the first 60,000 characters) into the task. `--image` sends a png, jpg, gif or webp picture; the model must support images. PDFs also work with `--file report.pdf`. Repeat a flag to attach more than one file.

## Common errors

| You see | What it means | What to do |
| --- | --- | --- |
| `Set ANTHROPIC_API_KEY first` | The key is not set in this terminal | `export ANTHROPIC_API_KEY="your-key"`. It lasts only for this terminal window: add the line to ~/.zshrc to keep it. |
| 401 or 403, "invalid API key" | The provider rejected the key | Copy the key again. No extra spaces or quotes inside it. A copy of the example text ("your-key") is not a key. Deleted or regenerated keys stop working. |
| 404, "model not found" or "no longer available" | The model name is wrong, retired, or not on your plan | Providers rename and retire models often. List what your key can use, then run: edit the MODEL line near the top of agent.ts. Names ending in `-latest` follow the provider's current model. |
| 400 | The provider refused the request itself | Read the "provider said" line: it names the field. Common causes: a tool schema the provider dislikes, or a model that does not support tools. |
| 429 | Rate limit or quota | Wait a minute, lower MAX_TURNS, or check billing and your plan's limits. Free tiers are small. |
| 500, 502, 503 "high demand" | The provider is overloaded | Temporary. Try again, or switch to a lighter model. The code already retries a few times, so a long pause before this error is normal. |
| It runs for a very long time | A slow or busy model, or the loop keeps going | Run with `--debug` to watch it. MAX_TURNS and TOKEN_BUDGET at the top of the file are hard limits: lower them while testing. Ctrl+C stops it. |
| `ERR_MODULE_NOT_FOUND` | Packages are not installed | Run `npm install` in this folder first. |
| "No module named ..." or "Cannot find module" | A package is missing | Run `npm install` in this folder. |
| `cannot find ...` after `--file` or `--image` | The path is wrong from where you ran the command | Use the full path, or `cd` into the folder that holds the file first. |
| 400 after `--image` | The model does not accept pictures | Pick a vision model, for example a current Claude, Gemini or GPT-4o class model, or a local one like llava. |
| The agent gives up or loops on the same step | The model is too weak for the task, or the tools return unhelpful results | Try a stronger model. Check what the tools return with `--debug`. Give it a more specific goal. |

## See which models your key can use

Open your provider's model list in its documentation or dashboard.

## Good habits

- Test with `--doctor` before the first real run, and again after changing MODEL or provider.
- Keep approval on while you learn what the agent does with its tools.
- Never paste your key into a chat, screenshot or public repository. If you did, delete it at the provider and make a new one.
- Provider model names change quickly. Treat MODEL as something you update.
