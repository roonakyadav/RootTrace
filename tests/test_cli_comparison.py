import unittest

from cli import build_parser


class CLIComparisonTests(unittest.TestCase):
    def test_compare_parser_accepts_repeated_agents(self):
        args = build_parser().parse_args(
            [
                "compare",
                "--agent",
                "dependency-aware",
                "--agent",
                "random",
                "--seed",
                "42",
            ]
        )
        self.assertEqual(args.command, "compare")
        self.assertEqual(args.agents, ["dependency-aware", "random"])
        self.assertEqual(args.seeds, [42])


if __name__ == "__main__":
    unittest.main()
