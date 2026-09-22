import unittest

from agents.rule_based import DependencyAwareAgent
from evaluation.runner import EpisodeRunner


class CounterfactualTraceTests(unittest.TestCase):
    def test_runner_can_record_local_regret(self):
        trace = EpisodeRunner().run(
            "easy-auth-down",
            DependencyAwareAgent(),
            seed=42,
            analyze_counterfactuals=True,
        )
        self.assertTrue(trace.steps)
        self.assertIsNotNone(trace.steps[0].local_regret)
        self.assertIsNotNone(trace.steps[0].best_counterfactual_reward)

    def test_normal_runner_does_not_pay_counterfactual_cost(self):
        trace = EpisodeRunner().run(
            "easy-auth-down",
            DependencyAwareAgent(),
            seed=42,
            analyze_counterfactuals=False,
        )
        self.assertIsNone(trace.steps[0].local_regret)


if __name__ == "__main__":
    unittest.main()
