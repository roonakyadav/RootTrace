import unittest

from env.dependencies import DependencyGraph


class DependencyGraphTests(unittest.TestCase):
    def test_task_topology_is_explicit(self):
        task = type("Task", (), {"id": "hard-cascading-failure"})()
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

    def test_serializable_mapping(self):
        graph = DependencyGraph.from_mapping({"auth": ["frontend"]})
        self.assertEqual(graph.as_dict(), {"auth": ["frontend"]})


if __name__ == "__main__":
    unittest.main()
