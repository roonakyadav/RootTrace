from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence

from agents.registry import create_agent
from evaluation.runner import EpisodeRunner


@dataclass(frozen=True)
class BenchmarkCase:
    task_id: str
    seed: int
    final_score: float
    success: bool
    total_reward: float
    steps: int
    unsafe_actions: int
    wasted_actions: int


@dataclass(frozen=True)
class BenchmarkMetrics:
    agent: str
    episodes: int
    success_rate: float
    mean_final_score: float
    mean_reward: float
    mean_steps: float
    unsafe_action_rate: float
    wasted_action_rate: float


@dataclass(frozen=True)
class BenchmarkReport:
    agent: str
    metrics: BenchmarkMetrics
    cases: tuple[BenchmarkCase, ...]

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent,
            "metrics": asdict(self.metrics),
            "cases": [asdict(case) for case in self.cases],
        }

    def save_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2),
            encoding="utf-8",
        )


class BenchmarkRunner:
    def __init__(self, episode_runner: EpisodeRunner | None = None) -> None:
        self.episode_runner = episode_runner or EpisodeRunner()

    def run_report(
        self,
        agent_name: str,
        task_ids: Sequence[str],
        seeds: Iterable[int] = (42,),
    ) -> BenchmarkReport:
        cases = []

        for seed in seeds:
            for task_id in task_ids:
                trace = self.episode_runner.run(
                    task_id,
                    create_agent(agent_name),
                    seed=seed,
                )
                result = trace.result
                if result is None:
                    raise RuntimeError(
                        f"Episode runner returned no result for {task_id}"
                    )

                unsafe = sum(
                    1
                    for step in trace.steps
                    if step.info.get("type") in {"wrong_fix", "unknown"}
                )

                cases.append(
                    BenchmarkCase(
                        task_id=task_id,
                        seed=seed,
                        final_score=result.final_score,
                        success=result.root_cause_score >= 1.0,
                        total_reward=sum(step.reward for step in trace.steps),
                        steps=result.steps_used,
                        unsafe_actions=unsafe,
                        wasted_actions=result.wasted_action_count,
                    )
                )

        if not cases:
            raise ValueError("Benchmark requires at least one task and seed")

        episodes = len(cases)
        metrics = BenchmarkMetrics(
            agent=agent_name,
            episodes=episodes,
            success_rate=sum(case.success for case in cases) / episodes,
            mean_final_score=sum(case.final_score for case in cases) / episodes,
            mean_reward=sum(case.total_reward for case in cases) / episodes,
            mean_steps=sum(case.steps for case in cases) / episodes,
            unsafe_action_rate=sum(case.unsafe_actions for case in cases)
            / max(sum(case.steps for case in cases), 1),
            wasted_action_rate=sum(case.wasted_actions for case in cases)
            / max(sum(case.steps for case in cases), 1),
        )
        return BenchmarkReport(
            agent=agent_name,
            metrics=metrics,
            cases=tuple(cases),
        )

    def run(
        self,
        agent_name: str,
        task_ids: Sequence[str],
        seeds: Iterable[int] = (42,),
    ) -> BenchmarkMetrics:
        return self.run_report(agent_name, task_ids, seeds).metrics

    @staticmethod
    def to_dict(metrics: BenchmarkMetrics) -> Dict:
        return asdict(metrics)

    @staticmethod
    def format_text(metrics: BenchmarkMetrics) -> str:
        return (
            f"agent={metrics.agent}\n"
            f"episodes={metrics.episodes}\n"
            f"success_rate={metrics.success_rate:.3f}\n"
            f"mean_final_score={metrics.mean_final_score:.3f}\n"
            f"mean_reward={metrics.mean_reward:.3f}\n"
            f"mean_steps={metrics.mean_steps:.2f}\n"
            f"unsafe_action_rate={metrics.unsafe_action_rate:.3f}\n"
            f"wasted_action_rate={metrics.wasted_action_rate:.3f}"
        )


DEFAULT_TASKS = (
    "easy-auth-down",
    "medium-payments-degraded",
    "hard-bad-deployment",
    "hard-cascading-failure",
    "hard-cascading-ambiguous",
    "hard-latent-root-cause",
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a RootTrace benchmark")
    parser.add_argument("--agent", default="dependency-aware")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--task", action="append", dest="tasks")
    parser.add_argument("--output", type=str, help="Write a JSON report to this path")
    args = parser.parse_args()

    report = BenchmarkRunner().run_report(
        agent_name=args.agent,
        task_ids=args.tasks or DEFAULT_TASKS,
        seeds=args.seeds or [42],
    )
    print(json.dumps(report.to_dict(), indent=2))

    if args.output:
        report.save_json(args.output)
