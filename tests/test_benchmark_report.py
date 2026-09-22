import json
import tempfile
import unittest
from pathlib import Path

from evaluation.benchmark import BenchmarkRunner


class BenchmarkReportTests(unittest.TestCase):
    def test_report_contains_per_case_results(self):
        report = BenchmarkRunner().run_report(
            "dependency-aware",
            ["easy-auth-down"],
            seeds=[42, 43],
        )
        self.assertEqual(len(report.cases), 2)
        self.assertEqual(report.metrics.episodes, 2)

    def test_report_round_trips_as_json(self):
        report = BenchmarkRunner().run_report(
            "dependency-aware",
            ["easy-auth-down"],
            seeds=[42],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report.save_json(path)
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["agent"], "dependency-aware")
            self.assertEqual(len(loaded["cases"]), 1)


if __name__ == "__main__":
    unittest.main()
