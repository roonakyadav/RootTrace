from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Sequence

from agents.registry import create_agent
from evaluation.runner import EpisodeRunner


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


class BenchmarkRunner:
    def __init__(self, episode_runner: EpisodeRunner | None = None) -> None:
        self.episode_runner = episode_runner or EpisodeRunner()

    def run(
        self,
        agent_name: str,
        task_ids: Sequence[str],
        seeds: Iterable[int] = (42,),
    ) -> BenchmarkMetrics:
        traces = []
        for seed in seeds:
            for task_id in task_ids:
                agent = create_agent(agent_name)
                traces.append(
                    self.episode_runner.run(task_id, agent, seed=seed)
                )

        if not traces:
            raise ValueError("Benchmark requires at least one task and seed")

        episodes = len(traces)
        successes = sum(
            1 for trace in traces
            if trace.result is not None and trace.result.root_cause_score >= 1.0
        )
        unsafe = 0
        wasted = 0
        total_steps = 0
        total_reward = 0.0
        total_score = 0.0

        for trace in traces:
            result = trace.result
            assert result is not None
            total_steps += result.steps_used
            total_score += result.final_score
            total_reward += sum(step.reward for step in trace.steps)

            unsafe += sum(
                1
                for step in trace.steps
                if step.info.get("type") in {"wrong_fix", "unknown"}
            )
            wasted += result.wasted_action_count

        return BenchmarkMetrics(
            agent=agent_name,
            episodes=episodes,
            success_rate=successes / episodes,
            mean_final_score=total_score / episodes,
            mean_reward=total_reward / episodes,
            mean_steps=total_steps / episodes,
            unsafe_action_rate=unsafe / max(total_steps, 1),
            wasted_action_rate=wasted / max(total_steps, 1),
        )

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
    import json

    parser = argparse.ArgumentParser(description="Run a RootTrace benchmark")
    parser.add_argument("--agent", default="dependency-aware")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--task", action="append", dest="tasks")
    args = parser.parse_args()

    metrics = BenchmarkRunner().run(
        agent_name=args.agent,
        task_ids=args.tasks or DEFAULT_TASKS,
        seeds=args.seeds or [42],
    )
    print(json.dumps(BenchmarkRunner.to_dict(metrics), indent=2))
