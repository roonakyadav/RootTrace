import random
import unittest

from env.dependencies import DependencyGraph
from env.faults import FaultInjector
from env.runtime import RuntimeState
from models.schemas import AutonomousDegradationPolicy, Service, ServiceStatus


class FaultInjectorPolicyTests(unittest.TestCase):
    def _injector(self):
        runtime = RuntimeState(
            services=[
                Service(name="db", status=ServiceStatus.DEGRADED),
                Service(name="auth", status=ServiceStatus.UP),
            ],
            logs=[],
            alerts=[],
        )
        return FaultInjector(
            runtime,
            DependencyGraph.from_mapping({"db": ["auth"]}),
            random.Random(42),
        )

    def test_accepts_typed_policy(self):
        injector = self._injector()
        self.assertTrue(
            injector.autonomous_degradation(
                AutonomousDegradationPolicy(enabled=True, interval=2)
            )
        )

    def test_accepts_mapping_policy(self):
        injector = self._injector()
        self.assertTrue(
            injector.autonomous_degradation({"enabled": True, "interval": 2})
        )


if __name__ == "__main__":
    unittest.main()
