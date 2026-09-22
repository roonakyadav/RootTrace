import unittest

from agents.random_agent import RandomAgent
from evaluation.runner import EpisodeRunner


class AgentSeedTests(unittest.TestCase):
    def test_random_agent_changes_sequence_with_episode_seed(self):
        agent = RandomAgent(seed=0)
        first = EpisodeRunner().run("easy-auth-down", agent, seed=1)
        second = EpisodeRunner().run("easy-auth-down", agent, seed=2)

        first_actions = [step.action["action_type"] for step in first.steps]
        second_actions = [step.action["action_type"] for step in second.steps]
        self.assertNotEqual(first_actions, second_actions)


if __name__ == "__main__":
    unittest.main()
