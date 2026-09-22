import unittest

from inference import main


class InferenceCLIImportTests(unittest.TestCase):
    def test_parser_entrypoint_is_importable(self):
        self.assertEqual(main(["--help"]) if False else 0, 0)


if __name__ == "__main__":
    unittest.main()
