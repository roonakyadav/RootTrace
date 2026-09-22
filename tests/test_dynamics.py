import unittest

from env.core import IncidentEnv
from env.dynamics import DynamicsEngine
from env.tasks import get_task


class DynamicsEngineTests(unittest.TestCase):
    def test_environment_owns_dynamics_engine(self):
        env = IncidentEnv(get_task("hard-cascading-failure"), seed=42)
        self.assertIsInstance(env.dynamics, DynamicsEngine)
        self.assertIs(env.dynamics.runtime, env.runtime)
        self.assertIs(env.dynamics.dependency_graph, env.dependency_graph)

    def test_cascade_wrapper_delegates(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        before = [service.status for service in env.runtime.services]
        env._apply_cascading_failures()
        after = [service.status for service in env.runtime.services]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
