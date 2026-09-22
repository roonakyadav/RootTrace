from __future__ import annotations

import random

from models.schemas import Action, ActionType, State


class RandomAgent:
    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def reset(self, seed: int | None = None) -> None:
        self.rng.seed(self.seed if seed is None else seed)

    def act(self, state: State) -> Action:
        actions = list(ActionType)
        action_type = self.rng.choice(
            [action for action in actions if action != ActionType.UNKNOWN]
        )

        service_names = [service.name for service in state.services]
        if action_type in {
            ActionType.ESCALATE,
            ActionType.IGNORE,
        }:
            target = "none"
        else:
            target = self.rng.choice(service_names)

        return Action(action_type=action_type, target=target)
