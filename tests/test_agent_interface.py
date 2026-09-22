import unittest

from agents.base import Agent
from agents.rule_based import DependencyAwareAgent
from env.tasks import get_task
from env.core import IncidentEnv


class AgentInterfaceTests(unittest.TestCase):
    def test_rule_based_agent_matches_agent_contract(self):
        agent = DependencyAwareAgent()
        env = IncidentEnv(get_task("hard-cascading-failure"), seed=42)
        self.assertTrue(isinstance(agent, Agent))
        self.assertEqual(agent.name, "dependency-aware")
        action = agent.act(env.state())
        self.assertIsNotNone(action.action_type)

    def test_backward_compatible_decide_action(self):
        agent = DependencyAwareAgent()
        env = IncidentEnv(get_task("easy-auth-down"), seed=42)
        self.assertEqual(agent.act(env.state()), agent.decide_action(env.state()))


if __name__ == "__main__":
    unittest.main()
