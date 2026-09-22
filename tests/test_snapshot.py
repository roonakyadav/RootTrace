import unittest

from env.core import IncidentEnv
from env.snapshot import EnvironmentSnapshot
from env.tasks import get_task
from models.schemas import Action, ActionType


class SnapshotTests(unittest.TestCase):
    def test_restore_replays_identical_transition(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        env.step(Action(action_type=ActionType.CHECK_LOGS, target="auth"))
        snapshot = env.snapshot()

        first = env.step(Action(action_type=ActionType.RESTART_SERVICE, target="auth"))
        first_state = first["state"].model_dump()

        env.restore(snapshot)
        second = env.step(Action(action_type=ActionType.RESTART_SERVICE, target="auth"))

        self.assertEqual(first_state, second["state"].model_dump())
        self.assertEqual(first["reward"], second["reward"])
        self.assertEqual(first["done"], second["done"])

    def test_snapshot_is_independent(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        snapshot = env.snapshot()
        self.assertIsInstance(snapshot, EnvironmentSnapshot)

        env.runtime.logs.append("mutated-after-snapshot")
        self.assertNotIn("mutated-after-snapshot", snapshot.runtime.logs)


if __name__ == "__main__":
    unittest.main()
