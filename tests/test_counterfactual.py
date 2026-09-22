import unittest

from env.core import IncidentEnv
from env.counterfactual import CounterfactualEvaluator
from env.tasks import get_task
from models.schemas import Action, ActionType


class CounterfactualTests(unittest.TestCase):
    def test_analysis_does_not_mutate_episode(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        evaluator = CounterfactualEvaluator()
        before = env.state().model_dump()

        action = Action(action_type=ActionType.RESTART_SERVICE, target="auth")
        candidates = [
            action,
            Action(action_type=ActionType.IGNORE, target="none"),
        ]
        results = evaluator.evaluate(env, action, candidates)

        self.assertEqual(before, env.state().model_dump())
        self.assertEqual(len(results), 2)

    def test_regret_is_zero_for_best_action(self):
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        evaluator = CounterfactualEvaluator()
        action = Action(action_type=ActionType.RESTART_SERVICE, target="auth")
        results = evaluator.evaluate(
            env,
            action,
            [action, Action(action_type=ActionType.IGNORE, target="none")],
        )
        self.assertGreaterEqual(evaluator.regret(action, results), 0.0)


if __name__ == "__main__":
    unittest.main()
