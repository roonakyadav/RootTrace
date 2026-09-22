import unittest
from unittest.mock import patch

from inference import main


class InferenceCLITests(unittest.TestCase):
    def test_help_exit_is_success(self):
        with self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_missing_llm_credentials_fail_cleanly(self):
        with patch.dict(
            "os.environ",
            {
                "LLM_API_KEY": "",
                "HF_TOKEN": "",
                "LLM_BASE_URL": "",
                "API_BASE_URL": "",
                "LLM_MODEL": "",
                "MODEL_NAME": "",
            },
            clear=False,
        ):
            with self.assertRaises(ValueError):
                main(["--task", "easy-auth-down", "--seed", "42"])


if __name__ == "__main__":
    unittest.main()
