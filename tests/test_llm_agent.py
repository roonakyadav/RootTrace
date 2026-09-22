import unittest

from agents.llm import LLMAgent, build_prompt
from models.schemas import Evidence, EvidenceType, Service, ServiceStatus, State


class LLMAgentTests(unittest.TestCase):
    def _state(self):
        return State(
            services=[Service(name="auth", status=ServiceStatus.DEGRADED)],
            logs=["auth timeout"],
            alerts=["WARNING: auth degraded"],
            time_step=2,
            bad_actions=0,
            history=[],
            system_health=0.75,
            total_cost=0.2,
            system_stability=0.7,
            risky_actions_count=0,
            dependencies={"auth": ["frontend"]},
            evidence=[
                Evidence(
                    id="log-0-0",
                    type=EvidenceType.LOG,
                    source="auth",
                    content="auth timeout",
                    timestamp=0,
                    reliability=0.8,
                )
            ],
        )

    def test_prompt_contains_structured_context(self):
        prompt = build_prompt(self._state())
        self.assertIn("DEPENDENCIES", prompt)
        self.assertIn("RECENT EVIDENCE", prompt)
        self.assertIn("auth timeout", prompt)

    def test_action_parser_is_strict(self):
        client = type("Client", (), {
            "chat": lambda self, prompt: '{"action_type":"check_logs","target":"auth"}'
        })()
        action = LLMAgent(client=client).act(self._state())
        self.assertEqual(action.action_type.value, "check_logs")
        self.assertEqual(action.target, "auth")

    def test_invalid_action_is_rejected(self):
        client = type("Client", (), {
            "chat": lambda self, prompt: '{"action_type":"make_coffee","target":"auth"}'
        })()
        with self.assertRaises(ValueError):
            LLMAgent(client=client).act(self._state())


if __name__ == "__main__":
    unittest.main()
