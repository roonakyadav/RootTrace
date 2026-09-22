import unittest

from models.schemas import EpisodeResult, State


class ModelDefaultTests(unittest.TestCase):
    def test_state_containers_are_not_shared(self):
        a = State(
            services=[],
            logs=[],
            alerts=[],
            time_step=0,
            bad_actions=0,
            history=[],
            system_health=1.0,
            total_cost=0.0,
            system_stability=1.0,
            risky_actions_count=0,
        )
        c = State(
            services=[],
            logs=[],
            alerts=[],
            time_step=0,
            bad_actions=0,
            history=[],
            system_health=1.0,
            total_cost=0.0,
            system_stability=1.0,
            risky_actions_count=0,
        )
        a.dependencies["db"] = ["auth"]
        a.diagnosed_targets.append("db")
        self.assertEqual(c.dependencies, {})
        self.assertEqual(c.diagnosed_targets, [])

    def test_episode_result_defaults_are_isolated(self):
        a = EpisodeResult(
            final_score=0.0,
            root_cause_score=0.0,
            efficiency_score=0.0,
            damage_score=0.0,
            cost_efficiency_score=0.0,
            stability_score=0.0,
            steps_used=0,
            bad_actions=0,
            system_health_penalty=0.0,
            total_cost=0.0,
        )
        c = EpisodeResult(
            final_score=0.0,
            root_cause_score=0.0,
            efficiency_score=0.0,
            damage_score=0.0,
            cost_efficiency_score=0.0,
            stability_score=0.0,
            steps_used=0,
            bad_actions=0,
            system_health_penalty=0.0,
            total_cost=0.0,
        )
        a.diagnosed_targets.append("auth")
        self.assertEqual(c.diagnosed_targets, [])


if __name__ == "__main__":
    unittest.main()
