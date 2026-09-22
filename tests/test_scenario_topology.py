import unittest

from env.dependencies import DependencyGraph
from env.scenarios import load_tasks


class ScenarioTopologyTests(unittest.TestCase):
    def test_topology_is_loaded_from_scenario(self):
        task = next(t for t in load_tasks() if t.id == "hard-latent-root-cause")
        graph = DependencyGraph.for_task(task)

        self.assertEqual(graph.dependents_of("payments"), ("auth",))
        self.assertEqual(graph.upstreams_of("auth"), ("payments",))

    def test_each_scenario_declares_a_topology(self):
        for task in load_tasks():
            self.assertTrue(task.dependencies, task.id)


if __name__ == "__main__":
    unittest.main()
