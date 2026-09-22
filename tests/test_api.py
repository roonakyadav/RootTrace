import unittest

from fastapi.testclient import TestClient

from api.main import app, session_store


class APISessionTests(unittest.TestCase):
    def setUp(self):
        session_store.clear()

    def test_reset_creates_unique_sessions(self):
        client = TestClient(app)
        first = client.post("/reset", json={"task_id": "easy", "seed": 1})
        second = client.post("/reset", json={"task_id": "easy", "seed": 2})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(
            first.json()["session_id"],
            second.json()["session_id"],
        )
        self.assertEqual(session_store.count(), 2)

    def test_session_step_and_state_are_isolated(self):
        client = TestClient(app)
        first = client.post("/reset", json={"task_id": "easy", "seed": 1}).json()
        second = client.post("/reset", json={"task_id": "easy", "seed": 2}).json()

        response = client.post(
            "/step",
            json={
                "session_id": first["session_id"],
                "action_type": "check_logs",
                "target": "auth",
            },
        )
        self.assertEqual(response.status_code, 200)

        first_state = client.get(
            "/state",
            params={"session_id": first["session_id"]},
        ).json()
        second_state = client.get(
            "/state",
            params={"session_id": second["session_id"]},
        ).json()

        self.assertEqual(first_state["time_step"], 1)
        self.assertEqual(second_state["time_step"], 0)

    def test_missing_session_is_clean_404(self):
        client = TestClient(app)
        response = client.get("/state", params={"session_id": "missing"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
