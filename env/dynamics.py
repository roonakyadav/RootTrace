from __future__ import annotations

import random

from env.dependencies import DependencyGraph
from env.faults import FaultInjector
from env.runtime import RuntimeState
from models.schemas import ActionType, ServiceStatus, Task


class DynamicsEngine:
    # Handles exogenous changes and dependency-driven recovery between actions.
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

    def propagate_failures(self) -> None:
        policy = self.task.dynamics.propagation
        if not policy.enabled:
            return

        degraded_interval = max(1, int(policy.degraded_interval))
        degraded_probability = float(policy.degraded_probability)

        for root, dependents in self.dependency_graph.items():
            if root in self.runtime.isolated_services:
                continue

            root_service = self._get_service(root)
            if not root_service or root_service.status == ServiceStatus.UP:
                continue

            for dependent_name in dependents:
                dependent = self._get_service(dependent_name)
                if not dependent or dependent.status == ServiceStatus.DOWN:
                    continue

                if root_service.status == ServiceStatus.DOWN:
                    dependent.status = policy.downstream_on_down
                elif (
                    root_service.status == ServiceStatus.DEGRADED
                    and dependent.status == ServiceStatus.UP
                    and self.runtime.time_step % degraded_interval == 0
                    and self.random.random() < degraded_probability
                ):
                    dependent.status = ServiceStatus.DEGRADED

    def recover_dependencies(self) -> None:
        for service in self.runtime.services:
            if service.status not in {ServiceStatus.DOWN, ServiceStatus.DEGRADED}:
                continue

            if self.true_root_cause == service.name and not self.runtime.root_cause_fixed:
                continue

            if (
                self.surface_symptom_target == service.name
                and self.true_root_cause
                and not self.runtime.root_cause_fixed
            ):
                continue

            upstreams = self.dependency_graph.upstreams_of(service.name)
            if not upstreams:
                continue

            dependencies_healthy = all(
                upstream is not None and upstream.status == ServiceStatus.UP
                for name in upstreams
                for upstream in [self._get_service(name)]
            )
            if dependencies_healthy:
                service.status = ServiceStatus.UP
                service.latency = 20
                service.error_rate = 0.01
                self.runtime.logs.append(
                    f"{service.name.capitalize()} recovered as dependencies stabilized"
                )

    def evolve(self) -> None:
        last_action = self.runtime.history[-1] if self.runtime.history else None

        if last_action and last_action.action_type == ActionType.IGNORE:
            if self.runtime.system_stability < 0.8:
                self.runtime.logs.append("No action taken, system instability persists")
                self.runtime.system_strain += 0.05

        self.recover_dependencies()
        self.propagate_failures()

        fault_policy = self.task.fault_policy.autonomous_degradation
        interval = int(fault_policy.get("interval", 0))
        if (
            self.runtime.time_step > 0
            and interval > 0
            and self.runtime.time_step % interval == 0
            and not self._all_services_up()
        ):
            self.fault_injector.autonomous_degradation(fault_policy)

        periodic_logs = self.task.dynamics.periodic_logs
        every = int(periodic_logs.interval)
        if every > 0 and self.runtime.time_step % every == 0:
            self.runtime.logs.append(
                str(periodic_logs.message)
            )

    # Compatibility seams used by the existing IncidentEnv controller.
    def _apply_cascading_failures(self) -> None:
        self.propagate_failures()
        self.recover_dependencies()

    def _evolve_env(self) -> None:
        self.evolve()

    def _autonomous_degradation(self):
        policy = self.task.fault_policy.autonomous_degradation
        return self.fault_injector.autonomous_degradation(policy)

    def _get_service(self, name: str):
        return next(
            (service for service in self.runtime.services if service.name == name),
            None,
        )

    def _all_services_up(self) -> bool:
        if self.runtime.fake_recovery_timer is not None and self.runtime.fake_recovery_timer > 0:
            return False
        return all(service.status == ServiceStatus.UP for service in self.runtime.services)
