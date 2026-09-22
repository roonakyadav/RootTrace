import random
import unittest

from env.dependencies import DependencyGraph
from env.runtime import RuntimeState
from env.telemetry import TelemetryEngine
from env.tasks import get_task
from models.schemas import Service, ServiceStatus


class TelemetryEngineTests(unittest.TestCase):
    def test_refresh_respects_service_status(self):
        task = get_task("easy-auth-down")
        runtime = RuntimeState(
            services=[Service(name="auth", status=ServiceStatus.DOWN)],
            logs=[],
            alerts=[],
        )
        graph = DependencyGraph.for_task(task)
        engine = TelemetryEngine(runtime, graph, random.Random(42))
        engine.refresh()

        self.assertEqual(runtime.services[0].latency, 1000.0)
        self.assertEqual(runtime.services[0].error_rate, 1.0)

    def test_refresh_is_seeded(self):
        service = Service(name="auth", status=ServiceStatus.UP)
        first = RuntimeState(services=[service.model_copy(deep=True)], logs=[], alerts=[])
        second = RuntimeState(services=[service.model_copy(deep=True)], logs=[], alerts=[])
        graph = DependencyGraph.from_mapping({})
        TelemetryEngine(first, graph, random.Random(42)).refresh()
        TelemetryEngine(second, graph, random.Random(42)).refresh()

        self.assertEqual(first.services[0].latency, second.services[0].latency)
        self.assertEqual(first.services[0].error_rate, second.services[0].error_rate)


if __name__ == "__main__":
    unittest.main()
