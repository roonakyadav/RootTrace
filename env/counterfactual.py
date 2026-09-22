from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from env.core import IncidentEnv
from models.schemas import Action, ActionType, State


@dataclass(frozen=True)
class Counterfactual:
    action: Action
    reward: float
    done: bool
    system_stability: float
    system_health: float
    bad_actions: int


class CounterfactualEvaluator:
    ACTION_TARGETS = {
        ActionType.ESCALATE: ("none",),
        ActionType.IGNORE: ("none",),
    }

    def candidates(self, state: State) -> Iterable[Action]:
        services = tuple(service.name for service in state.services)
        for action_type in ActionType:
            if action_type == ActionType.UNKNOWN:
                continue
            targets = self.ACTION_TARGETS.get(action_type, services)
            for target in targets:
                yield Action(action_type=action_type, target=target)

    def evaluate(
        self,
        env: IncidentEnv,
        chosen_action: Action | None = None,
        candidates: Iterable[Action] | None = None,
    ) -> List[Counterfactual]:
        snapshot = env.snapshot()
        state = env.state()
        actions = list(candidates or self.candidates(state))

        results = []
        try:
            for action in actions:
                env.restore(snapshot)
                result = env.step(action)
                next_state = result["state"]
                results.append(
                    Counterfactual(
                        action=action,
                        reward=float(result["reward"]),
                        done=bool(result["done"]),
                        system_stability=next_state.system_stability,
                        system_health=next_state.system_health,
                        bad_actions=next_state.bad_actions,
                    )
                )
        finally:
            env.restore(snapshot)

        if chosen_action is not None and not any(
            candidate.action == chosen_action for candidate in results
        ):
            raise ValueError("chosen_action must be included in candidates")

        return sorted(
            results,
            key=lambda item: (
                item.reward,
                item.system_stability,
                item.system_health,
            ),
            reverse=True,
        )

    def regret(self, chosen_action: Action, results: Iterable[Counterfactual]) -> float:
        results = list(results)
        chosen = next(
            (item for item in results if item.action == chosen_action),
            None,
        )
        if chosen is None:
            raise ValueError("chosen_action is missing from counterfactual results")

        best_reward = max(item.reward for item in results)
        return max(0.0, best_reward - chosen.reward)
