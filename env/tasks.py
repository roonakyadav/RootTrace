from typing import Optional

from env.scenarios import load_tasks
from models.schemas import Task


TASKS = load_tasks()


def get_task(task_id: str) -> Optional[Task]:
    return next((task for task in TASKS if task.id == task_id), None)


def test_hard_task_state() -> None:
    task = get_task("hard-cascading-failure")
    if not task:
        print("HARD task not found!")
        return

    print("--- Initial State of HARD Task ---")
    print(f"Description: {task.description}")
    print("Services:")
    for service in task.initial_services:
        print(f"  - {service.name}: {service.status}")
    print("Logs:")
    for log in task.initial_logs:
        print(f"  - {log}")
    print("Alerts:")
    for alert in task.initial_alerts:
        print(f"  - {alert}")
    print("---------------------------------")
