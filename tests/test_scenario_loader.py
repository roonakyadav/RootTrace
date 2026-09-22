import unittest

from env.scenarios import load_tasks


class ScenarioLoaderTests(unittest.TestCase):
    def test_all_scenarios_load(self):
        tasks = load_tasks()
        self.assertEqual(len(tasks), 6)
        self.assertEqual(tasks[0].id, "easy-auth-down")
        self.assertEqual(tasks[-1].id, "hard-latent-root-cause")

    def test_hidden_root_cause_metadata_survives(self):
        task = next(t for t in load_tasks() if t.id == "hard-latent-root-cause")
        self.assertEqual(task.true_root_cause, "payments")
        self.assertEqual(task.surface_symptom_target, "auth")


if __name__ == "__main__":
    unittest.main()
