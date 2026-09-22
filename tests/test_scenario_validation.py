import unittest

from env.scenarios import load_tasks
from env.validation import validate_task, validate_tasks


class ScenarioValidationTests(unittest.TestCase):
    def test_all_checked_in_scenarios_are_valid(self):
        tasks = load_tasks()
        validate_tasks(tasks)

    def test_current_scenario_has_valid_root_cause(self):
        task = next(t for t in load_tasks() if t.id == "hard-bad-deployment")
        self.assertEqual(validate_task(task), [])

    def test_invalid_dependency_is_rejected(self):
        task = next(t for t in load_tasks() if t.id == "easy-auth-down")
        mutated = task.model_copy(deep=True)
        mutated.dependencies["missing"] = ["auth"]
        self.assertIn(
            "dependency source 'missing' is not a known service",
            validate_task(mutated),
        )


if __name__ == "__main__":
    unittest.main()
