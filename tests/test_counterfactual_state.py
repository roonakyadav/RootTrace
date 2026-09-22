import unittest

from env.core import IncidentEnv
from env.counterfactual import CounterfactualEvaluator
from env.tasks import get_task
from models.schemas import Action, ActionType


class CounterfactualStateTests(unittest.TestCase):
    def test_evaluation_preserves_evidence_exactly(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        before = env.state().model_dump()

        CounterfactualEvaluator().evaluate(
            env,
            candidates=[
                Action(action_type=ActionType.CHECK_LOGS, target="auth"),
                Action(action_type=ActionType.RESTART_SERVICE, target="auth"),
            ],
        )

        self.assertEqual(before, env.state().model_dump())


if __name__ == "__main__":
    unittest.main()
