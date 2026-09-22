import unittest

from env.core import IncidentEnv
from env.tasks import get_task


class RuntimeStateTests(unittest.TestCase):
    def test_episode_state_is_isolated(self):
        task = get_task("easy-auth-down")
        first = IncidentEnv(task, seed=42)
        second = IncidentEnv(task, seed=42)

        first.runtime.logs.append("only-first-episode")
        first.runtime.services[0].status = "up"

        self.assertNotIn("only-first-episode", second.runtime.logs)
        self.assertNotEqual(first.runtime.services[0].status, second.runtime.services[0].status)

    def test_initial_state_is_built_from_task(self):
        task = get_task("hard-bad-deployment")
        env = IncidentEnv(task, seed=42)

        self.assertEqual(env.runtime.time_step, 0)
        self.assertEqual(len(env.runtime.services), len(task.initial_services))
        self.assertEqual(env.runtime.logs, task.initial_logs)


if __name__ == "__main__":
    unittest.main()
