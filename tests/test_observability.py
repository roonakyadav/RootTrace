import random
import unittest

from env.dependencies import DependencyGraph
from env.observability import ObservabilityEngine
from env.runtime import RuntimeState
from env.tasks import get_task
from models.schemas import Action, ActionType, Service, ServiceStatus


class ObservabilityEngineTests(unittest.TestCase):
    def test_alerts_reflect_runtime_state(self):
        task = get_task("easy-auth-down")
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.DOWN)],
            logs=[],
            alerts=[],
        )
        ObservabilityEngine(runtime, DependencyGraph.for_task(task), task, random.Random(42)).refresh_alerts()
        self.assertEqual(runtime.alerts, ["CRITICAL: auth is down"])

    def test_action_log_is_bounded(self):
        task = get_task("easy-auth-down")
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.DOWN)],
            logs=[f"log-{i}" for i in range(20)],
            alerts=[],
        )
        ObservabilityEngine(runtime, DependencyGraph.for_task(task), task, random.Random(42)).record_action(
            Action(action_type=ActionType.RESTART_SERVICE, target="auth"),
            {"type": "correct_fix"},
        )
        self.assertEqual(len(runtime.logs), 10)
        self.assertIn("Auth service recovered successfully", runtime.logs)


if __name__ == "__main__":
    unittest.main()
