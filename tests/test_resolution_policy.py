import unittest

from env.resolution import matching_resolution, missing_diagnosis
from env.scenarios import load_tasks
from models.schemas import Action, ActionType


class ResolutionPolicyTests(unittest.TestCase):
    def test_resolution_is_declared_not_task_specific(self):
        task = next(t for t in load_tasks() if t.id == "hard-cascading-ambiguous")
        action = Action(action_type=ActionType.ROLLBACK_SERVICE, target="payments")
        rule = matching_resolution(task, action)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.action, ActionType.ROLLBACK_SERVICE)

    def test_required_diagnosis_is_enforced_from_metadata(self):
        task = next(t for t in load_tasks() if t.id == "hard-bad-deployment")
        action = Action(action_type=ActionType.ROLLBACK_SERVICE, target="auth")
        missing = missing_diagnosis(
            task,
            [Action(action_type=ActionType.CHECK_LOGS, target="auth")],
        )
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].action, ActionType.CHECK_METRICS)
        self.assertEqual(missing[0].target, "auth")


if __name__ == "__main__":
    unittest.main()
