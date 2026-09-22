from __future__ import annotations

import argparse
import json
from pathlib import Path

from env.scenarios import load_tasks
from env.validation import validate_tasks
from evaluation.benchmark import BenchmarkRunner, DEFAULT_TASKS
from evaluation.compare import compare_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roottrace",
        description="Run and evaluate causal incident environments for AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Start the RootTrace API server")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=7860)

    validate = subparsers.add_parser("validate", help="Validate all scenario definitions")
    validate.add_argument("--directory", type=Path, default=None)

    benchmark = subparsers.add_parser("benchmark", help="Run an agent benchmark")
    benchmark.add_argument("--agent", default="dependency-aware")
    benchmark.add_argument("--task", action="append", dest="tasks")
    benchmark.add_argument("--seed", action="append", type=int, dest="seeds")
    benchmark.add_argument("--output", type=Path)

    compare = subparsers.add_parser("compare", help="Compare two or more agents")
    compare.add_argument(
        "--agent",
        action="append",
        dest="agents",
        required=True,
        help="Agent name; repeat for each agent to compare",
    )
    compare.add_argument("--task", action="append", dest="tasks")
    compare.add_argument("--seed", action="append", type=int, dest="seeds")
    compare.add_argument("--output", type=Path)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("api.main:app", host=args.host, port=args.port)
        return 0

    if args.command == "validate":
        tasks = load_tasks(args.directory) if args.directory else load_tasks()
        validate_tasks(tasks)
        print(f"Validated {len(tasks)} scenarios.")
        return 0

    if args.command == "benchmark":
        report = BenchmarkRunner().run_report(
            agent_name=args.agent,
            task_ids=args.tasks or DEFAULT_TASKS,
            seeds=args.seeds or [42],
        )
        print(json.dumps(report.to_dict(), indent=2))
        if args.output:
            report.save_json(args.output)
        return 0

    if args.command == "compare":
        runner = BenchmarkRunner()
        reports = [
            runner.run_report(
                agent_name=agent_name,
                task_ids=args.tasks or DEFAULT_TASKS,
                seeds=args.seeds or [42],
            )
            for agent_name in args.agents
        ]
        result = compare_reports(reports)
        payload = result.to_dict()
        print(json.dumps(payload, indent=2))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
