from __future__ import annotations

from typing import Protocol, runtime_checkable

from models.schemas import Action, State


@runtime_checkable
class Agent(Protocol):
    name: str

    def reset(self, seed: int | None = None) -> None:
        ...

    def act(self, state: State) -> Action:
        ...
