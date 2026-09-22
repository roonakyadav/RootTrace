import unittest

from evaluation.benchmark import BenchmarkRunner
from evaluation.compare import compare_reports


class BenchmarkComparisonTests(unittest.TestCase):
    def test_comparison_is_machine_readable(self):
        runner = BenchmarkRunner()
        reports = [
            runner.run_report("dependency-aware", ["easy-auth-down"], seeds=[42]),
            runner.run_report("random", ["easy-auth-down"], seeds=[42]),
        ]
        comparison = compare_reports(reports)

        self.assertEqual(comparison.agents, ("dependency-aware", "random"))
        self.assertEqual(
            comparison.deltas["dependency-aware"]["mean_final_score_delta"],
            0.0,
        )
        self.assertIn("random", comparison.reports)


if __name__ == "__main__":
    unittest.main()
