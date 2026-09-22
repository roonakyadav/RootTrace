import unittest

from env.core import IncidentEnv
from env.scenarios import get_task


class DynamicsEngineTests(unittest.TestCase):
    def test_environment_owns_dynamics_engine(self):
        env = IncidentEnv(get_task("hard-cascading-failure"), seed=42)
        self.assertIsNotNone(env.dynamics)
        self.assertIs(env.dynamics.runtime, env.runtime)
        self.assertIs(env.dynamics.dependency_graph, env.dependency_graph)

    def test_declared_dependency_failure_propagates(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        env.runtime.time_step = 2
        env.dynamics.propagate_failures()

        frontend = next(
            service for service in env.runtime.services
            if service.name == "frontend"
        )
        self.assertEqual(frontend.status.value, "down")

    def test_root_fix_allows_dependency_recovery(self):
        env = IncidentEnv(get_task("hard-cascading-failure"), seed=42)
        db = next(service for service in env.runtime.services if service.name == "db")
        auth = next(service for service in env.runtime.services if service.name == "auth")
        db.status = "up"
        env.runtime.root_cause_fixed = True
        env.dynamics.recover_dependencies()
        self.assertEqual(auth.status.value, "up")


if __name__ == "__main__":
    unittest.main()
