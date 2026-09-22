import unittest

from env.core import IncidentEnv
from env.tasks import TASKS, get_task


class EnvironmentSmokeTests(unittest.TestCase):
    def test_every_task_can_reset_and_step(self):
        self.assertEqual(len(TASKS), 6)

        for task in TASKS:
            env = IncidentEnv(task, seed=42)
            state = env.state()
            self.assertEqual(state.time_step, 0)
            self.assertGreaterEqual(state.system_stability, 0.0)
            self.assertLessEqual(state.system_stability, 1.0)

            result = env.step(self._first_diagnostic_action(task))
            self.assertIsNotNone(result["reward"])
            self.assertIn("state", result)
            self.assertIn("done", result)

    def test_task_lookup(self):
        task = get_task("hard-bad-deployment")
        self.assertIsNotNone(task)
        self.assertEqual(task.id, "hard-bad-deployment")

    @staticmethod
    def _first_diagnostic_action(task):
        from models.schemas import Action, ActionType
        return Action(
            action_type=ActionType.CHECK_LOGS,
            target=task.initial_services[0].name,
        )


if __name__ == "__main__":
    unittest.main()
