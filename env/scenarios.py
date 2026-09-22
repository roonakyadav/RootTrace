from pathlib import Path
from typing import List, Optional

import yaml

from models.schemas import Service, ServiceStatus, Task, TaskDifficulty


SCENARIO_DIR = Path(__file__).with_name("scenarios")


def _build_task(data: dict) -> Task:
    required = ["id", "difficulty", "description", "goal", "max_steps", "services"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Scenario is missing required fields: {', '.join(missing)}")

    services = [
        Service(
            name=item["name"],
            status=ServiceStatus(item["status"]),
            latency=float(item.get("latency", 0.0)),
            error_rate=float(item.get("error_rate", 0.0)),
        )
        for item in data["services"]
    ]

    if not services:
        raise ValueError(f"Scenario {data['id']} must define at least one service")

    return Task(
        id=str(data["id"]),
        difficulty=TaskDifficulty(data["difficulty"]),
        description=str(data["description"]),
        goal=str(data["goal"]),
        max_steps=int(data["max_steps"]),
        success_conditions=dict(data.get("success_conditions", {})),
        failure_conditions=dict(data.get("failure_conditions", {})),
        initial_services=services,
        initial_logs=list(data.get("initial_logs", [])),
        initial_alerts=list(data.get("initial_alerts", [])),
        true_root_cause=data.get("true_root_cause"),
        surface_symptom_target=data.get("surface_symptom_target"),
        diagnosis_requirements=list(data.get("diagnosis_requirements", [])),
        resolution_actions=list(data.get("resolution_actions", [])),
        fault_policy=dict(data.get("fault_policy", {})),
        dependencies={
            str(source): [str(target) for target in targets]
            for source, targets in dict(data.get("dependencies", {})).items()
        },
    )


def load_tasks(directory: Path = SCENARIO_DIR) -> List[Task]:
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise FileNotFoundError(f"No scenario files found in {directory}")

    tasks = []
    seen_ids = set()

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        task = _build_task(data)
        if task.id in seen_ids:
            raise ValueError(f"Duplicate scenario id: {task.id}")
        seen_ids.add(task.id)
        tasks.append(task)

    return tasks
