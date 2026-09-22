import unittest

from models.schemas import Task, State


class SchemaPlacementTests(unittest.TestCase):
    def test_dynamics_belongs_to_task(self):
        self.assertIn("dynamics", Task.model_fields)
        self.assertNotIn("dynamics", State.model_fields)

    def test_evidence_belongs_to_public_state(self):
        self.assertIn("evidence", State.model_fields)
        self.assertNotIn("evidence", Task.model_fields)


if __name__ == "__main__":
    unittest.main()
