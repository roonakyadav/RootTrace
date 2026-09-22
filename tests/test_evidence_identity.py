import unittest

from env.core import IncidentEnv
from env.tasks import get_task
from models.schemas import Action, ActionType


class EvidenceIdentityTests(unittest.TestCase):
    def test_restore_reuses_deterministic_evidence_ids(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        snapshot = env.snapshot()

        env.step(Action(action_type=ActionType.CHECK_LOGS, target="auth"))
        ids_after_first = [item.id for item in env.runtime.evidence]

        env.restore(snapshot)
        env.step(Action(action_type=ActionType.CHECK_LOGS, target="auth"))

        ids_after_restore = [item.id for item in env.runtime.evidence]
        self.assertEqual(len(ids_after_restore), len(set(ids_after_restore)))
        self.assertEqual(ids_after_first[-1], ids_after_restore[-1])


if __name__ == "__main__":
    unittest.main()
