from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Sequence

from evaluation.benchmark import BenchmarkReport


@dataclass(frozen=True)
class AgentComparison:
    agents: tuple[str, ...]
    reports: Dict[str, Dict]
    deltas: Dict[str, Dict[str, float]]

    def to_dict(self) -> Dict:
        return {
            "agents": list(self.agents),
            "reports": self.reports,
            "deltas": self.deltas,
        }


def compare_reports(reports: Sequence[BenchmarkReport]) -> AgentComparison:
    if not reports:
        raise ValueError("At least one benchmark report is required")

    agent_names = tuple(report.agent for report in reports)
    baseline = reports[0].metrics

    deltas = {}
    for report in reports:
        metrics = report.metrics
        deltas[report.agent] = {
            "success_rate_delta": metrics.success_rate - baseline.success_rate,
            "mean_final_score_delta": metrics.mean_final_score - baseline.mean_final_score,
            "mean_reward_delta": metrics.mean_reward - baseline.mean_reward,
            "mean_steps_delta": metrics.mean_steps - baseline.mean_steps,
            "unsafe_action_rate_delta": metrics.unsafe_action_rate - baseline.unsafe_action_rate,
            "wasted_action_rate_delta": metrics.wasted_action_rate - baseline.wasted_action_rate,
        }

    return AgentComparison(
        agents=agent_names,
        reports={report.agent: report.to_dict() for report in reports},
        deltas=deltas,
    )
