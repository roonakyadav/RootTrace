from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from env.runtime import RuntimeState


@dataclass(frozen=True)
class EnvironmentSnapshot:
    runtime: RuntimeState
    rng_state: Any

    def copy(self) -> "EnvironmentSnapshot":
        return EnvironmentSnapshot(
            runtime=deepcopy(self.runtime),
            rng_state=deepcopy(self.rng_state),
        )
