from __future__ import annotations

import random

from env.dependencies import DependencyGraph
from env.faults import FaultInjector
from env.runtime import RuntimeState
from models.schemas import ActionType, ServiceStatus, Task, TaskDifficulty


class DynamicsEngine:
    def __init__(
        self,
        runtime: RuntimeState,
        dependency_graph: DependencyGraph,
        task: Task,
        fault_injector: FaultInjector,
        rng: random.Random,
        true_root_cause: str | None = None,
        surface_symptom_target: str | None = None,
    ) -> None:
        self.runtime = runtime
        self.dependency_graph = dependency_graph
        self.task = task
        self.fault_injector = fault_injector
        self.random = rng
        self.true_root_cause = true_root_cause
        self.surface_symptom_target = surface_symptom_target

    def _apply_cascading_failures(self):
        for root, dependents in self.dependency_graph.items():
            if root in self.runtime.isolated_services:
                continue

            root_service = self._get_service(root)
            if not root_service:
                continue

            for dep_name in dependents:
                dep_service = self._get_service(dep_name)
                if not dep_service:
                    continue

                if root_service.status == ServiceStatus.DOWN:
                    if root == "db":
                        if dep_name == "auth":
                            dep_service.status = ServiceStatus.DOWN
                        elif dep_name == "payments":
                            dep_service.status = ServiceStatus.DEGRADED
                    elif root == "auth":
                        if dep_name == "frontend":
                            dep_service.status = ServiceStatus.DEGRADED
                elif root_service.status == ServiceStatus.DEGRADED:
                    # BUG FIX 4: Only cascade once per degradation event, not every step
                    # Use time_step modulo to limit cascading frequency
                    if (dep_service.status == ServiceStatus.UP and 
                        self.random.random() < 0.85 and 
                        self.runtime.time_step % 2 == 0):  # Only check every 2 steps
                        dep_service.status = ServiceStatus.DEGRADED
                elif root_service.status == ServiceStatus.UP:
                    if dep_service.status == ServiceStatus.DEGRADED:
                        pass  # Recovery handled by _evolve_env

        for service in self.runtime.services:
            if service.status == ServiceStatus.DEGRADED:
                upstreams = self.dependency_graph.upstreams_of(service.name)

                if upstreams:
                    dependencies_healthy = all(
                        self._get_service(dep).status == ServiceStatus.UP
                        for dep in upstreams
                    )

                    if dependencies_healthy:
                        if self.task.id == "hard-latent-root-cause" and service.name == self.surface_symptom_target:
                            if not self.runtime.root_cause_fixed:
                                continue

                        service.status = ServiceStatus.UP
                        service.latency = 20
                        service.error_rate = 0.01
                        self.runtime.logs.append(f"{service.name.capitalize()} recovered as dependencies stabilized")

    def _evolve_env(self):
        last_action = self.runtime.history[-1] if self.runtime.history else None

        if last_action and last_action.action_type == ActionType.IGNORE:
            if self.runtime.system_stability < 0.8:
                self.runtime.logs.append("No action taken, system instability persists")
                self.runtime.system_strain += 0.05

        if self.task.difficulty == TaskDifficulty.HARD:
            db_service = next((s for s in self.runtime.services if s.name == "db"), None)
            auth_service = next((s for s in self.runtime.services if s.name == "auth"), None)
            payments_service = next((s for s in self.runtime.services if s.name == "payments"), None)

            base_threshold = 2 if self.runtime.system_strain < 0.5 else 3
            recovery_threshold = base_threshold + self.random.randint(-1, 1)
            recovery_threshold = max(1, recovery_threshold)

            if db_service and db_service.status == ServiceStatus.UP:
                if auth_service and auth_service.status == ServiceStatus.DOWN:
                    # ISSUE 4 FIX: Check if optimize_db was EVER called, not just at specific index
                    optimize_db_called = any(
                        a.action_type == ActionType.OPTIMIZE_DB and a.target == "db"
                        for a in self.runtime.history
                    )
                    if optimize_db_called:
                        auth_service.status = ServiceStatus.UP

                elif auth_service and auth_service.status == ServiceStatus.UP:
                    if payments_service and payments_service.status == ServiceStatus.DEGRADED:
                        if len(self.runtime.history) >= (recovery_threshold + 1):
                            payments_service.status = ServiceStatus.UP

            fault_policy = self.task.fault_policy.get("autonomous_degradation", {})
            interval = int(fault_policy.get("interval", 0))
            if (
                self.runtime.time_step > 0
                and interval > 0
                and self.runtime.time_step % interval == 0
                and not self._all_services_up()
            ):
                self._autonomous_degradation()

        elif self.task.difficulty == TaskDifficulty.MEDIUM:
            if self.runtime.time_step % 3 == 0:
                self.runtime.logs.append(f"Spurious log entry at step {self.runtime.time_step}")

            auth_service = next((s for s in self.runtime.services if s.name == "auth"), None)
            payment_service = next((s for s in self.runtime.services if s.name == "payments"), None)

            if auth_service and auth_service.status == ServiceStatus.DOWN:
                down_steps = sum(1 for a in self.runtime.history if a.action_type == ActionType.IGNORE or a.action_type == ActionType.CHECK_LOGS)
                if down_steps >= 2:
                    if payment_service and payment_service.status == ServiceStatus.UP:
                        payment_service.status = ServiceStatus.DEGRADED

    def _autonomous_degradation(self):
        policy = self.task.fault_policy.get("autonomous_degradation", {})
        return self.fault_injector.autonomous_degradation(policy)

    def _get_service(self, name: str):
        return next((service for service in self.runtime.services if service.name == name), None)

    def _all_services_up(self) -> bool:
        if self.runtime.fake_recovery_timer is not None and self.runtime.fake_recovery_timer > 0:
            return False
        return all(service.status == ServiceStatus.UP for service in self.runtime.services)

