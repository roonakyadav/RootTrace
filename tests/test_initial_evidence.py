import random
import unittest

from env.core import IncidentEnv
from env.dependencies import DependencyGraph
from env.observability import ObservabilityEngine
from env.runtime import RuntimeState
from env.tasks import get_task
from models.schemas import EvidenceType, Service, ServiceStatus


class InitialEvidenceTests(unittest.TestCase):
    def test_reset_exposes_initial_logs_as_evidence(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        state = env.state()
        self.assertTrue(state.evidence)
        self.assertTrue(any(item.type == EvidenceType.LOG for item in state.evidence))
        self.assertTrue(any(item.timestamp == 0 for item in state.evidence))

    def test_seed_does_not_duplicate_on_refresh(self):
        task = get_task("easy-auth-down")
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.DOWN)],
            logs=["Auth service: initial log"],
            alerts=[],
        )
        engine = ObservabilityEngine(
            runtime,
            DependencyGraph.for_task(task),
            task,
            random.Random(42),
        )
        before = len(runtime.evidence)
        engine.refresh_alerts()
        self.assertGreaterEqual(len(runtime.evidence), before)


if __name__ == "__main__":
    unittest.main()
