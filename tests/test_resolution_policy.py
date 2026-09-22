import unittest

from env.resolution import matching_resolution, missing_diagnosis
from env.scenarios import load_tasks
from models.schemas import Action, ActionType


class ResolutionPolicyTests(unittest.TestCase):
    def test_resolution_is_declared_not_task_specific(self):
        task = next(t for t in load_tasks() if t.id == "hard-cascading-ambiguous")
        action = Action(action_type=ActionType.ROLLBACK_SERVICE, target="payments")
        self.assertIsNotNone(matching_resolution(task, action))

    def test_required_diagnosis_is_enforced_from_metadata(self):
        task = next(t for t in load_tasks() if t.id == "hard-bad-deployment")
        action = Action(action_type=ActionType.ROLLBACK_SERVICE, target="auth")
        self.assertEqual(
            missing_diagnosis(task, [Action(action_type=ActionType.CHECK_LOGS, target="auth")]),
            [{"action": "check_metrics", "target": "auth"}],
        )


if __name__ == "__main__":
    unittest.main()
