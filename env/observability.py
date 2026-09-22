from __future__ import annotations

import random
from typing import Any, Dict

from env.dependencies import DependencyGraph
from env.runtime import RuntimeState
from models.schemas import Action, ServiceStatus, Task


class ObservabilityEngine:
    # Produces the logs and alerts exposed to an agent.
    def __init__(self, runtime: RuntimeState, dependency_graph: DependencyGraph, task: Task, rng: random.Random) -> None:
        self.runtime = runtime
        self.dependency_graph = dependency_graph
        self.task = task
        self.rng = rng

    def refresh_alerts(self) -> None:
        alerts = []
        for service in self.runtime.services:
            if service.status == ServiceStatus.DOWN:
                alerts.append(f"CRITICAL: {service.name} is down")
            elif service.status == ServiceStatus.DEGRADED:
                alerts.append(f"WARNING: {service.name} degraded")
        self.runtime.alerts = alerts

    def record_action(self, action: Action, reward_info: Dict[str, Any]) -> None:
        logs = []
        if reward_info["type"] == "correct_fix":
            logs.append(f"{action.target.capitalize()} service recovered successfully")
        elif reward_info["type"] == "wrong_fix":
            logs.append(f"Failed to fix {action.target.capitalize()}: dependency unresolved")
        elif reward_info["type"] == "useless_action":
            logs.append(f"Action {action.action_type} on {action.target} had no impact")

        if self.rng.random() < 0.25:
            logs.append(self.rng.choice([
                "INFO: Background job completed successfully",
                "INFO: System health check passed",
                "INFO: Routine log rotation completed",
                "INFO: Minor latency variation observed in secondary cluster",
            ]))

        for service in self.runtime.services:
            for root in self.dependency_graph.upstreams_of(service.name):
                upstream = self._service(root)
                if not upstream:
                    continue
                if service.status == ServiceStatus.DEGRADED and upstream.status != ServiceStatus.UP:
                    logs.append(f"{service.name.capitalize()} degraded due to {root} failure")
                    break
                if service.status == ServiceStatus.DOWN and upstream.status == ServiceStatus.DOWN:
                    logs.append(f"{service.name.capitalize()} offline due to {root} outage")
                    break

        if self.runtime.system_stability < 0.5:
            logs.append("System instability reaching critical levels")

        self._scenario_logs(logs)
        self.runtime.logs.extend(logs)
        self.runtime.logs = self.runtime.logs[-10:]

    def _scenario_logs(self, logs) -> None:
        if self.task.id == "hard-cascading-failure" and self.runtime.time_step % 2 == 0:
            logs.append(self.rng.choice([
                "WARN: Payments service instability detected (possible root cause)",
                "ERROR: Frontend experiencing cascading failures from payments",
                "WARN: Auth service showing signs of failure - investigate immediately",
                "INFO: Recommendation: Focus on stabilizing payments service first",
            ]))

        if self.task.id == "hard-latent-root-cause":
            if self.runtime.time_step == 1:
                logs.append("INFO: cross-service dependency check: auth -> (unresolved_upstream)")
            elif self.runtime.time_step == 3:
                logs.append("WARN: payments service internal queue depth increasing subtly")
            elif self.runtime.time_step == 6:
                logs.append("INFO: deployment logs show payments-v3.5.0 has shared resources with auth mesh")

        if self.task.id == "hard-bad-deployment":
            if self.runtime.time_step == 1:
                logs.append("DB: WARN - connection spike correlated with auth errors (investigate DB first?)")
            elif self.runtime.time_step == 2:
                logs.append("DB: INFO - all internal DB health checks passing, disk IO normal")
            elif self.runtime.time_step == 4:
                logs.append("Auth service: ERROR - goroutine count: 8,412 (expected: <500) — possible memory leak in v2.1.0")

    def _service(self, name: str):
        return next((service for service in self.runtime.services if service.name == name), None)
