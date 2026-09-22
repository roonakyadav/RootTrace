from __future__ import annotations

import argparse
import json
import os

from agents.llm import LLMAgent
from evaluation.benchmark import BenchmarkRunner, DEFAULT_TASKS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a RootTrace LLM benchmark")
    parser.add_argument("--task", action="append", dest="tasks")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    agent = LLMAgent(
        api_key=os.getenv("LLM_API_KEY") or os.getenv("HF_TOKEN"),
        base_url=os.getenv("LLM_BASE_URL") or os.getenv("API_BASE_URL"),
        model=os.getenv("LLM_MODEL") or os.getenv("MODEL_NAME"),
    )
    # Registering an ad-hoc agent instance keeps provider configuration out of
    # the global registry while reusing the standard benchmark machinery.
    runner = BenchmarkRunner()

    traces = []
    tasks = args.tasks or DEFAULT_TASKS
    seeds = args.seeds or [42]

    for seed in seeds:
        for task_id in tasks:
            trace = runner.episode_runner.run(task_id, agent, seed=seed)
            traces.append(trace)

    payload = {
        "agent": agent.name,
        "episodes": len(traces),
        "results": [
            {
                "task_id": trace.task_id,
                "seed": trace.seed,
                "final_score": trace.result.final_score if trace.result else None,
                "steps": trace.result.steps_used if trace.result else None,
            }
            for trace in traces
        ],
    }

    print(json.dumps(payload, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
