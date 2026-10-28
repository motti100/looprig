"""chain-meeting-follow-up (OpenAI Agents SDK version)
Reason: direct | Act: no tools | Observe: raw | Decide: stop when done | Shape: prompt chain

Exported by Looprig. This keeps your model, system prompt, tools, approval setting and turn limit,
and hands the loop itself to the OpenAI Agents SDK. Looprig-only techniques (tree of thoughts,
reflection, team shapes, MCP, structured output) are not carried over: use the main agent file for those.

  pip install "openai-agents[litellm]"
  export ANTHROPIC_API_KEY=...
  python agent_agents_sdk.py "your task"
"""
import json
import os
import sys

from agents import Agent, ModelSettings, Runner
from agents.extensions.models.litellm_model import LitellmModel

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096
MAX_TURNS = 10  # model calls allowed in one run
SYSTEM = """You are Chain Meeting Follow Up, an AI agent.

Goal: Turn raw meeting notes into decisions, action items with owners, and a short recap email.

Answer from your own knowledge and reasoning. If you are missing information, say what is missing.

Rules:
- Be accurate. If you are unsure, say so instead of guessing.
- Keep answers concise and well structured.
- Never take an irreversible action unless the user asked for it."""


APPROVAL = "risky"  # "none" | "risky" | "all": ask before running tools
RISKY = {"write_file", "run_python", "my_custom_tool"}


def approved(name, args):
    if APPROVAL == "all" or (APPROVAL == "risky" and name in RISKY):
        return input(f"\n  approve {name}({json.dumps(args)[:200]})? [y/N] ").strip().lower() == "y"
    return True


# No tools selected: this agent answers from the model alone.

agent = Agent(
    name="chain-meeting-follow-up",
    instructions=SYSTEM,
    model=LitellmModel(model="anthropic/" + MODEL, api_key=os.environ.get("ANTHROPIC_API_KEY")),
    model_settings=ModelSettings(max_tokens=MAX_TOKENS),
    tools=[],
)


def run(task):
    return Runner.run_sync(agent, task, max_turns=MAX_TURNS).final_output


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Notes: we agreed to ship v2 on the 14th. Priya owns the migration. Tom to confirm pricing by Friday."))
