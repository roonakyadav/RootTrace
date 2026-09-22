import random
import unittest

from env.dependencies import DependencyGraph
from env.evidence import EvidenceStore
from env.observability import ObservabilityEngine
from env.runtime import RuntimeState
from env.scenarios import load_tasks
from models.schemas import EvidenceType, Service, ServiceStatus


class EvidenceTests(unittest.TestCase):
    def test_store_tracks_source_type_and_reliability(self):
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.UP)],
            logs=[],
            alerts=[],
        )
        store = EvidenceStore(runtime)
        item = store.ingest_log("Auth service: timeout", timestamp=4, reliability=0.42)
        self.assertEqual(item.type, EvidenceType.LOG)
        self.assertEqual(item.source, "auth service")
        self.assertEqual(item.timestamp, 4)
        self.assertEqual(item.reliability, 0.42)

    def test_observability_adds_initial_and_action_evidence(self):
        task = next(t for t in load_tasks() if t.id == "easy-auth-down")
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.DOWN)],
            logs=[],
            alerts=[],
        )
        engine = ObservabilityEngine(
            runtime,
            DependencyGraph.for_task(task),
            task,
            random.Random(42),
        )
        engine.refresh_alerts()
        engine.record_action(
            type("Action", (), {"target": "auth", "action_type": "restart_service"})(),
            {"type": "correct_fix"},
        )
        self.assertGreaterEqual(len(runtime.evidence), 1)
        self.assertTrue(any(item.type == EvidenceType.ALERT for item in runtime.evidence))


if __name__ == "__main__":
    unittest.main()
