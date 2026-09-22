from __future__ import annotations

import random
from typing import Iterable

from env.dependencies import DependencyGraph
from env.runtime import RuntimeState
from models.schemas import ServiceStatus


class TelemetryEngine:
    """Generate service telemetry from operational state."""

    def __init__(
        self,
        runtime: RuntimeState,
        dependency_graph: DependencyGraph,
        rng: random.Random,
        risk_threshold: float = 0.5,
    ) -> None:
        self.runtime = runtime
        self.dependency_graph = dependency_graph
        self.rng = rng
        self.risk_threshold = risk_threshold

    def refresh(self) -> None:
        for service in self.runtime.services:
            self._refresh_service(service)

    def _refresh_service(self, service) -> None:
        if service.status == ServiceStatus.UP:
            service.latency = 20 + (10 * self.runtime.system_strain)
            service.error_rate = 0.01 + (0.05 * self.runtime.system_strain)
        elif service.status == ServiceStatus.DEGRADED:
            service.latency = 200 + (100 * self.runtime.system_strain)
            service.error_rate = 0.15 + (0.1 * self.runtime.system_strain)
        else:
            service.latency = 1000.0
            service.error_rate = 1.0

        for isolated_name in self.runtime.isolated_services:
            if service.name in self.dependency_graph.dependents_of(isolated_name):
                service.latency *= 1.5

        if service.name == "frontend" and self.runtime.drained_services:
            service.error_rate *= 0.5

        if service.name in self.runtime.partial_fixes:
            service.error_rate = 0.5

        service.latency *= 1 + self.rng.uniform(-0.05, 0.05)
        service.error_rate *= 1 + self.rng.uniform(-0.05, 0.05)

        if self.runtime.hidden_risk > 0:
            risk_multiplier = 1.0 + (
                min(self.runtime.hidden_risk, self.risk_threshold) * 0.2
            )
            service.latency *= risk_multiplier

        service.latency = max(1.0, service.latency)
        service.error_rate = max(0.0, min(1.0, service.error_rate))
