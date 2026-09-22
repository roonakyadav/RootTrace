import unittest

from env.dependencies import DependencyGraph
from env.scenarios import load_tasks


class DependencyGraphTests(unittest.TestCase):
    def test_task_topology_is_loaded_from_scenario(self):
        task = next(
            task for task in load_tasks()
            if task.id == "hard-cascading-failure"
        )
        graph = DependencyGraph.for_task(task)
        self.assertEqual(graph.dependents_of("db"), ("auth",))
        self.assertEqual(
            graph.transitive_dependents_of("db"),
            ("auth", "frontend", "payments"),
        )

    def test_upstream_lookup(self):
        graph = DependencyGraph.from_mapping({
            "db": ["auth"],
            "auth": ["payments"],
            "payments": ["frontend"],
        })
        self.assertEqual(graph.upstreams_of("frontend"), ("payments",))
        self.assertEqual(
            graph.transitive_upstreams_of("frontend"),
            ("auth", "db", "payments"),
        )

    def test_state_mapping_is_serializable(self):
        graph = DependencyGraph.from_mapping({"auth": ["frontend"]})
        self.assertEqual(graph.as_dict(), {"auth": ["frontend"]})


if __name__ == "__main__":
    unittest.main()
