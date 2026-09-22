import unittest

from agents.rule_based import DependencyAwareAgent
from evaluation.runner import EpisodeRunner


class EpisodeRunnerTests(unittest.TestCase):
    def test_runner_produces_replayable_trace(self):
        trace = EpisodeRunner().run(
            "easy-auth-down",
            DependencyAwareAgent(),
            seed=42,
        )

        self.assertEqual(trace.task_id, "easy-auth-down")
        self.assertEqual(trace.agent_name, "dependency-aware")
        self.assertGreater(len(trace.steps), 0)
        self.assertIsNotNone(trace.result)
        self.assertEqual(
            trace.to_dict()["steps"][0]["action"]["target"],
            trace.steps[0].action["target"],
        )


if __name__ == "__main__":
    unittest.main()
