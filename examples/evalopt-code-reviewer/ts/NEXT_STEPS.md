# What to do next with evalopt-code-reviewer

## 1. Run it once
Put the file in an empty folder, open a terminal there, and run:

    npm i @anthropic-ai/sdk && npm i -D tsx typescript @types/node
    export ANTHROPIC_API_KEY="..."
    npx tsx agent.ts "Review app.py and list the three most serious problems."

Your settings use the evaluator, so use the full agent.ts. The short version leaves those out.

## 2. If it does not start
Run `npx tsx agent.ts --doctor`. It checks your key, the model and one tool call, one step at a time, and tells you the next fix. The Help tab lists common errors.

## 3. Find out if it is any good
Open evals.ts and replace the example cases with five real tasks you care about, each with what a good answer must contain. Run it after every change, so you can see whether a change helped or hurt.

## 4. Make it yours
- Change what it does by editing the SYSTEM text near the top.
- Give it a new ability by adding a tool: a description the model reads, and a function that runs.
- Keep the limits (maximum turns and tokens) until you trust it. They stop a confused agent from running up a bill.

## 5. Share or deploy it
The Deploy kit tab has a Dockerfile and a small web server so other people can use it. Keep your key in an environment variable, never in the code.
