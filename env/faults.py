from __future__ import annotations

import random
from typing import Dict, List

from env.dependencies import DependencyGraph
from env.runtime import RuntimeState
from models.schemas import ServiceStatus


class FaultInjector:
    # Apply controlled exogenous failures to an episode.
    def __init__(
        self,
        runtime: RuntimeState,
        dependency_graph: DependencyGraph,
        rng: random.Random,
    ) -> None:
        self.runtime = runtime
        self.dependency_graph = dependency_graph
        self.rng = rng

    def autonomous_degradation(self, policy: Dict) -> bool:
        if not policy.get("enabled", False):
            return False
        if self.runtime.root_cause_fixed:
            return False

        candidates = self._dependent_candidates()
        if not candidates:
            excluded = set(policy.get("exclude_services", []))
            candidates = [
                service
                for service in self.runtime.services
                if service.status == ServiceStatus.UP and service.name not in excluded
            ]

        if not candidates:
            return False

        target = self.rng.choice(candidates)
        target.status = ServiceStatus.DEGRADED
        target.error_rate = min(1.0, target.error_rate + 0.3)
        self.runtime.logs.append(
            f"WARN: {target.name} degrading autonomously — unresolved root cause spreading"
        )
        self.runtime.system_strain += 0.1
        return True

    def _dependent_candidates(self):
        candidates = []
        for root, dependents in self.dependency_graph.items():
            root_service = self._service(root)
            if root_service and root_service.status != ServiceStatus.UP:
                for dependent in dependents:
                    service = self._service(dependent)
                    if service and service.status == ServiceStatus.UP:
                        candidates.append(service)
        return candidates

    def _service(self, name):
        return next(
            (service for service in self.runtime.services if service.name == name),
            None,
        )
