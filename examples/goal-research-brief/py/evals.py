"""Smoke tests for goal-research-brief. Edit CASES, then run:  python evals.py"""

import importlib.util
import sys

spec = importlib.util.spec_from_file_location("agent", "agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)
agent.APPROVAL = "none"  # tests must not wait for a person

CASES = [
    {
        "task": "What are the main trade-offs between SQLite and Postgres for a small SaaS product?",
        "must_contain": [],      # strings the answer has to include, e.g. ["postgres", "sqlite"]
        "must_not_contain": [],  # strings that signal a failure, e.g. ["i cannot"]
        "max_tokens": 100000,
    },
]


def main():
    failed = 0
    for i, case in enumerate(CASES, 1):
        before = agent.used_tokens()
        answer = agent.run(case["task"])
        low = answer.lower()
        missing = [s for s in case["must_contain"] if s.lower() not in low]
        banned = [s for s in case["must_not_contain"] if s.lower() in low]
        spent = agent.used_tokens() - before
        ok = not missing and not banned and spent <= case["max_tokens"] and not answer.startswith("[stopped")
        print(("PASS" if ok else "FAIL") + f" case {i}: {case['task'][:60]}  ({spent} tokens)")
        if not ok:
            failed += 1
            print("   missing:", missing, "banned found:", banned)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
