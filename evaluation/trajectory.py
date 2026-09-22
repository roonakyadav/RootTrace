from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.schemas import Action, EpisodeResult, State


@dataclass
class TraceStep:
    step: int
    state_before: Dict[str, Any]
    action: Dict[str, Any]
    reward: float
    state_after: Dict[str, Any]
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)
    local_regret: float | None = None
    best_counterfactual_reward: float | None = None


@dataclass
class EpisodeTrace:
    task_id: str
    agent_name: str
    seed: int
    steps: List[TraceStep] = field(default_factory=list)
    result: EpisodeResult | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "seed": self.seed,
            "steps": [
                {
                    "step": item.step,
                    "state_before": item.state_before,
                    "action": item.action,
                    "reward": item.reward,
                    "state_after": item.state_after,
                    "done": item.done,
                    "info": item.info,
                    "local_regret": item.local_regret,
                    "best_counterfactual_reward": item.best_counterfactual_reward,
                }
                for item in self.steps
            ],
            "result": self.result.model_dump() if self.result else None,
        }
