import unittest

from cli import build_parser


class CLITests(unittest.TestCase):
    def test_benchmark_parser(self):
        args = build_parser().parse_args(
            ["benchmark", "--agent", "random", "--seed", "42", "--output", "out.json"]
        )
        self.assertEqual(args.command, "benchmark")
        self.assertEqual(args.agent, "random")
        self.assertEqual(args.seeds, [42])
        self.assertEqual(str(args.output), "out.json")

    def test_validate_parser(self):
        args = build_parser().parse_args(["validate"])
        self.assertEqual(args.command, "validate")


if __name__ == "__main__":
    unittest.main()
