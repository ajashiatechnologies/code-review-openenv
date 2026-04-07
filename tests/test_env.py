"""
tests/test_env.py
Integration tests for the Code Review OpenEnv FastAPI server.
Run with: pytest tests/test_env.py -v
Requires the server to NOT be running (uses TestClient).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from env.environment import app

client = TestClient(app)


class TestHealthEndpoint:

    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestResetEndpoint:

    def test_reset_easy_returns_observation(self):
        r = client.post("/reset", params={"task": "easy"})
        assert r.status_code == 200
        obs = r.json()
        assert "session_id" in obs
        assert "diff" in obs
        assert "language" in obs
        assert "file_name" in obs
        assert obs["step_num"] == 0

    def test_reset_medium_works(self):
        r = client.post("/reset", params={"task": "medium"})
        assert r.status_code == 200

    def test_reset_hard_works(self):
        r = client.post("/reset", params={"task": "hard"})
        assert r.status_code == 200

    def test_reset_invalid_task_returns_400(self):
        r = client.post("/reset", params={"task": "impossible"})
        assert r.status_code == 400

    def test_reset_returns_unique_session_ids(self):
        ids = set()
        for _ in range(5):
            r = client.post("/reset", params={"task": "easy"})
            ids.add(r.json()["session_id"])
        assert len(ids) == 5, "session_id must be unique per reset"


class TestStepEndpoint:

    def _reset(self, task="easy"):
        r = client.post("/reset", params={"task": task})
        return r.json()

    def test_step_returns_valid_step_result(self):
        obs   = self._reset("easy")
        sid   = obs["session_id"]
        action = {"action_type": "detect", "issue_types": ["bug"]}
        r = client.post("/step", json=action, params={"session_id": sid})
        assert r.status_code == 200
        result = r.json()
        assert "observation" in result
        assert "reward" in result
        assert "done" in result
        assert "info" in result

    def test_reward_in_valid_range(self):
        obs    = self._reset("easy")
        sid    = obs["session_id"]
        action = {"action_type": "detect", "issue_types": ["none"]}
        r      = client.post("/step", json=action, params={"session_id": sid})
        reward = r.json()["reward"]
        assert -1.0 <= reward <= 1.0

    def test_step_without_reset_returns_400(self):
        action = {"action_type": "detect", "issue_types": ["bug"]}
        r = client.post("/step", json=action, params={"session_id": "nonexistent-session"})
        assert r.status_code == 400

    def test_episode_terminates_after_max_steps(self):
        obs   = self._reset("easy")
        sid   = obs["session_id"]
        done  = False
        steps = 0
        while not done and steps < 10:
            action = {"action_type": "detect", "issue_types": ["none"]}
            r      = client.post("/step", json=action, params={"session_id": sid})
            result = r.json()
            done   = result["done"]
            steps += 1
        assert done, "Episode must terminate"
        assert steps <= 5, "Episode must not exceed max_steps"

    def test_two_sessions_are_independent(self):
        """Two simultaneous sessions must not interfere."""
        obs1 = self._reset("easy")
        obs2 = self._reset("hard")
        sid1, sid2 = obs1["session_id"], obs2["session_id"]
        assert sid1 != sid2

        a1 = {"action_type": "detect", "issue_types": ["bug"]}
        a2 = {"action_type": "classify", "severity": "critical"}
        r1 = client.post("/step", json=a1, params={"session_id": sid1})
        r2 = client.post("/step", json=a2, params={"session_id": sid2})
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestStateEndpoint:

    def test_state_matches_reset_observation(self):
        obs = client.post("/reset", params={"task": "easy"}).json()
        sid = obs["session_id"]
        state = client.get("/state", params={"session_id": sid}).json()
        assert state["diff"]      == obs["diff"]
        assert state["file_name"] == obs["file_name"]

    def test_state_without_session_returns_400(self):
        r = client.get("/state", params={"session_id": "bad-id"})
        assert r.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
