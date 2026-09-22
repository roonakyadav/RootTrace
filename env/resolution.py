from __future__ import annotations

from typing import Any, Dict, Iterable, List

from models.schemas import Action, ActionType, Task


FIX_ACTIONS = {
    ActionType.RESTART_SERVICE,
    ActionType.ROLLBACK_SERVICE,
    ActionType.SCALE,
    ActionType.OPTIMIZE_DB,
}


def matching_resolution(task: Task, action: Action) -> Dict[str, str] | None:
    """Return the declared resolution matching an action, if any."""
    for rule in task.resolution_actions:
        if rule.action == action.action_type and rule.target == action.target:
            return rule
    return None


def missing_diagnosis(task: Task, history: Iterable[Action]) -> List[Dict[str, str]]:
    """Return required evidence that has not yet been collected."""
    history_pairs = {
        (action.action_type, action.target)
        for action in history
        if action.action_type in {ActionType.CHECK_LOGS, ActionType.CHECK_METRICS}
    }
    return [
        requirement
        for requirement in task.diagnosis_requirements
        if (requirement.action, requirement.target) not in history_pairs
    ]


def is_fix_action(action: Action) -> bool:
    return action.action_type in FIX_ACTIONS
