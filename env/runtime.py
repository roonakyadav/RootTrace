from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from models.schemas import Evidence, Service, Task


@dataclass
class RuntimeState:
    """Mutable state belonging to one incident episode."""

    services: List[Service]
    logs: List[str]
    alerts: List[str]
    evidence: List[Evidence] = field(default_factory=list)

    time_step: int = 0
    history: List[Any] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)

    bad_actions: int = 0
    total_cost: float = 0.0
    risky_actions_count: int = 0
    system_strain: float = 0.0
    previous_strain: float = 0.0

    isolated_services: List[str] = field(default_factory=list)
    drained_services: List[str] = field(default_factory=list)
    partial_fixes: List[str] = field(default_factory=list)
    redegrade_timers: Dict[str, int] = field(default_factory=dict)

    symptom_fix_count: int = 0
    root_cause_step: Optional[int] = None
    delayed_failure_count: int = 0
    wasted_action_count: int = 0
    diagnosis_streak: int = 0
    diagnosed_targets: Set[str] = field(default_factory=set)

    hidden_risk: float = 0.0
    side_effect_triggered: bool = False
    consecutive_diagnosis_count: int = 0
    diagnosis_penalty_applied: bool = False

    fake_recovery_timer: Optional[int] = None
    root_cause_fixed: bool = False

    system_stability: float = 0.0
    previous_stability: float = 0.0
    is_done: bool = False

    @classmethod
    def from_task(cls, task: Task) -> "RuntimeState":
        services = [Service(**service.model_dump()) for service in task.initial_services]
        return cls(
            services=services,
            logs=list(task.initial_logs),
            alerts=list(task.initial_alerts),
        )
