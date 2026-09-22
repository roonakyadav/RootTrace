import unittest

from env.core import IncidentEnv
from env.tasks import get_task


class DynamicsPolicyTests(unittest.TestCase):
    def test_latent_symptom_does_not_auto_recover(self):
        env = IncidentEnv(get_task("hard-latent-root-cause"), seed=42)
        env._apply_cascading_failures()
        auth = next(service for service in env.runtime.services if service.name == "auth")
        self.assertEqual(auth.status.value, "degraded")

    def test_root_fix_allows_dependency_recovery(self):
        env = IncidentEnv(get_task("hard-cascading-failure"), seed=42)
        db = next(service for service in env.runtime.services if service.name == "db")
        auth = next(service for service in env.runtime.services if service.name == "auth")
        db.status = "up"
        env.runtime.root_cause_fixed = True
        env._apply_cascading_failures()
        self.assertEqual(auth.status.value, "up")


if __name__ == "__main__":
    unittest.main()
