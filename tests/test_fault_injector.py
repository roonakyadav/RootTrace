import random
import unittest

from env.dependencies import DependencyGraph
from env.faults import FaultInjector
from env.runtime import RuntimeState
from env.scenarios import load_tasks
from models.schemas import Service, ServiceStatus


class FaultInjectorTests(unittest.TestCase):
    def test_disabled_policy_does_nothing(self):
        runtime = RuntimeState(
            services=[Service(name="db", status=ServiceStatus.UP)],
            logs=[],
            alerts=[],
        )
        injector = FaultInjector(runtime, DependencyGraph.from_mapping({}), random.Random(42))
        changed = injector.autonomous_degradation({"enabled": False})
        self.assertFalse(changed)
        self.assertEqual(runtime.services[0].status, ServiceStatus.UP)

    def test_enabled_policy_degrades_dependent_service(self):
        task = next(t for t in load_tasks() if t.id == "hard-cascading-failure")
        runtime = RuntimeState(
            services=[
                Service(name="db", status=ServiceStatus.DEGRADED),
                Service(name="auth", status=ServiceStatus.UP),
            ],
            logs=[],
            alerts=[],
        )
        injector = FaultInjector(runtime, DependencyGraph.for_task(task), random.Random(42))
        changed = injector.autonomous_degradation({"enabled": True, "interval": 2})
        self.assertTrue(changed)
        self.assertEqual(runtime.services[1].status, ServiceStatus.DEGRADED)


if __name__ == "__main__":
    unittest.main()
