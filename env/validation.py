from __future__ import annotations

from typing import Iterable, List

from models.schemas import ActionType, Task


VALID_DIAGNOSIS_ACTIONS = {
    ActionType.CHECK_LOGS.value,
    ActionType.CHECK_METRICS.value,
}


def validate_task(task: Task) -> List[str]:
    errors: List[str] = []
    service_names = [service.name for service in task.initial_services]
    service_set = set(service_names)

    if len(service_names) != len(service_set):
        errors.append("service names must be unique")
    if not service_names:
        errors.append("at least one service is required")
    if task.max_steps <= 0:
        errors.append("max_steps must be greater than zero")

    if task.true_root_cause is not None and task.true_root_cause not in service_set:
        errors.append(f"true_root_cause {task.true_root_cause!r} is not a known service")

    if (
        task.surface_symptom_target is not None
        and task.surface_symptom_target not in service_set
    ):
        errors.append(
            f"surface_symptom_target {task.surface_symptom_target!r} is not a known service"
        )

    valid_actions = {action.value for action in ActionType if action != ActionType.UNKNOWN}

    for index, rule in enumerate(task.resolution_actions):
        action = rule.action.value
        target = rule.target
        if action not in valid_actions:
            errors.append(f"resolution_actions[{index}] has invalid action {action!r}")
        if target not in service_set:
            errors.append(
                f"resolution_actions[{index}] targets unknown service {target!r}"
            )
        if task.true_root_cause and target != task.true_root_cause:
            errors.append(
                f"resolution_actions[{index}] must target true_root_cause {task.true_root_cause!r}"
            )

    for index, rule in enumerate(task.diagnosis_requirements):
        action = rule.action.value
        target = rule.target
        if action not in VALID_DIAGNOSIS_ACTIONS:
            errors.append(
                f"diagnosis_requirements[{index}] has invalid diagnostic action {action!r}"
            )
        if target not in service_set:
            errors.append(
                f"diagnosis_requirements[{index}] targets unknown service {target!r}"
            )

    for source, dependents in task.dependencies.items():
        if source not in service_set:
            errors.append(f"dependency source {source!r} is not a known service")
        for target in dependents:
            if target not in service_set:
                errors.append(
                    f"dependency target {target!r} is not a known service"
                )
            if target == source:
                errors.append(f"service {source!r} cannot depend on itself")

    fault_policy = task.fault_policy.autonomous_degradation
    if fault_policy.enabled:
        interval = int(fault_policy.interval)
        if interval <= 0:
            errors.append("autonomous_degradation.interval must be greater than zero")
        for name in fault_policy.exclude_services:
            if name not in service_set:
                errors.append(
                    f"fault_policy.exclude_services contains unknown service {name!r}"
                )

    return errors


def validate_tasks(tasks: Iterable[Task]) -> None:
    failures = []
    for task in tasks:
        errors = validate_task(task)
        if errors:
            failures.append(f"{task.id}: " + "; ".join(errors))

    if failures:
        raise ValueError("Invalid RootTrace scenarios:\n" + "\n".join(failures))
