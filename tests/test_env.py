import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from env.environment import TASK_MAX_STEPS, app  # noqa: E402

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_healthy_status(self):
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert payload["environment"] == "code-review-openenv"


class TestResetEndpoint:
    @pytest.mark.parametrize("task", ["easy", "medium", "hard"])
    def test_reset_returns_expected_observation(self, task):
        response = client.post("/reset", params={"task": task})
        assert response.status_code == 200
        obs = response.json()
        assert "session_id" in obs
        assert "diff" in obs
        assert "language" in obs
        assert "file_name" in obs
        assert obs["step_num"] == 0
        assert obs["max_steps"] == TASK_MAX_STEPS[task]

    def test_reset_rejects_invalid_task(self):
        response = client.post("/reset", params={"task": "impossible"})
        assert response.status_code == 400

    def test_reset_returns_unique_session_ids(self):
        session_ids = {
            client.post("/reset", params={"task": "easy"}).json()["session_id"]
            for _ in range(5)
        }
        assert len(session_ids) == 5


class TestStepEndpoint:
    def _reset(self, task="easy"):
        return client.post("/reset", params={"task": task}).json()

    def test_step_returns_strict_open_interval_reward(self):
        obs = self._reset("easy")
        response = client.post(
            "/step",
            json={"action_type": "detect", "issue_types": ["none"]},
            params={"session_id": obs["session_id"]},
        )
        assert response.status_code == 200
        reward = response.json()["reward"]
        assert 0.0 < reward < 1.0

    def test_step_includes_progress_metadata(self):
        obs = self._reset("hard")
        response = client.post(
            "/step",
            json={"action_type": "detect", "issue_types": ["security"]},
            params={"session_id": obs["session_id"]},
        )
        payload = response.json()
        assert payload["info"]["step"] == 1
        assert "episode_id" in payload["info"]
        assert "total_reward" in payload["info"]

    def test_step_without_reset_returns_400(self):
        response = client.post(
            "/step",
            json={"action_type": "detect", "issue_types": ["bug"]},
            params={"session_id": "missing"},
        )
        assert response.status_code == 400

    def test_episode_stops_at_task_specific_max_steps(self):
        obs = self._reset("easy")
        session_id = obs["session_id"]
        done = False
        steps = 0

        while not done and steps < 10:
            response = client.post(
                "/step",
                json={"action_type": "detect", "issue_types": ["none"]},
                params={"session_id": session_id},
            )
            payload = response.json()
            done = payload["done"]
            steps += 1

        assert done is True
        assert steps <= TASK_MAX_STEPS["easy"]


class TestSchemaEndpoint:
    def test_schema_exposes_state_contract(self):
        response = client.get("/schema")
        assert response.status_code == 200
        payload = response.json()
        assert "action" in payload
        assert "observation" in payload
        assert "state" in payload


class TestStateEndpoint:
    def test_state_matches_current_observation(self):
        obs = client.post("/reset", params={"task": "easy"}).json()
        session_id = obs["session_id"]
        state = client.get("/state", params={"session_id": session_id}).json()
        assert state["diff"] == obs["diff"]
        assert state["file_name"] == obs["file_name"]

    def test_state_without_session_returns_400(self):
        response = client.get("/state", params={"session_id": "bad-id"})
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
