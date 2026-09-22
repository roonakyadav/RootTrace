import unittest

from evaluation.benchmark import BenchmarkRunner


class BenchmarkRunnerTests(unittest.TestCase):
    def test_benchmark_is_deterministic_for_a_fixed_seed(self):
        runner = BenchmarkRunner()
        first = runner.run(
            "dependency-aware",
            ["easy-auth-down"],
            seeds=[42],
        )
        second = runner.run(
            "dependency-aware",
            ["easy-auth-down"],
            seeds=[42],
        )
        self.assertEqual(
            BenchmarkRunner.to_dict(first),
            BenchmarkRunner.to_dict(second),
        )

    def test_multiple_tasks_are_aggregated(self):
        metrics = BenchmarkRunner().run(
            "dependency-aware",
            ["easy-auth-down", "medium-payments-degraded"],
            seeds=[42],
        )
        self.assertEqual(metrics.episodes, 2)
        self.assertGreaterEqual(metrics.success_rate, 0.0)
        self.assertLessEqual(metrics.success_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
