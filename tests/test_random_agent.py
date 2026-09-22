import unittest

from agents.random_agent import RandomAgent
from models.schemas import ActionType, State, Service, ServiceStatus


class RandomAgentTests(unittest.TestCase):
    def _state(self):
        return State(
            services=[
                Service(name="auth", status=ServiceStatus.DOWN),
                Service(name="frontend", status=ServiceStatus.UP),
            ],
            logs=[],
            alerts=[],
            time_step=0,
            bad_actions=0,
            history=[],
            system_health=0.5,
            total_cost=0.0,
            system_stability=0.5,
            risky_actions_count=0,
        )

    def test_random_agent_is_reproducible(self):
        first = RandomAgent(seed=42)
        second = RandomAgent(seed=42)
        first.reset()
        second.reset()
        sequence_one = [first.act(self._state()).model_dump() for _ in range(5)]
        sequence_two = [second.act(self._state()).model_dump() for _ in range(5)]
        self.assertEqual(sequence_one, sequence_two)

    def test_random_agent_never_emits_unknown_action(self):
        agent = RandomAgent(seed=42)
        for _ in range(20):
            self.assertNotEqual(agent.act(self._state()).action_type, ActionType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
