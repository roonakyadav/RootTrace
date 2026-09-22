import unittest

from env.scenarios import load_tasks


class ScenarioLoaderTests(unittest.TestCase):
    def test_all_scenarios_load(self):
        tasks = load_tasks()
        self.assertEqual(len(tasks), 6)
        self.assertEqual(tasks[0].id, "easy-auth-down")
        self.assertEqual(tasks[-1].id, "hard-latent-root-cause")

    def test_resolution_metadata_survives_as_typed_models(self):
        task = next(t for t in load_tasks() if t.id == "hard-bad-deployment")
        self.assertEqual(task.true_root_cause, "auth")
        self.assertEqual(task.resolution_actions[0].action.value, "rollback_service")
        self.assertEqual(task.resolution_actions[0].target, "auth")
        self.assertEqual(task.diagnosis_requirements[1].action.value, "check_metrics")
        self.assertEqual(task.diagnosis_requirements[1].target, "auth")


if __name__ == "__main__":
    unittest.main()
