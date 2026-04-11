import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from env.graders import (  # noqa: E402
    MAX_SCORE,
    MIN_SCORE,
    grade_action,
    grade_detection,
    grade_full_review,
    grade_severity,
)
from env.models import Action, IssueType, Severity  # noqa: E402
from tasks.easy_task import TASK_CONFIG as EASY_TASK  # noqa: E402
from tasks.hard_task import TASK_CONFIG as HARD_TASK  # noqa: E402
from tasks.medium_task import TASK_CONFIG as MEDIUM_TASK  # noqa: E402


NONE_CODE = {
    "ground_truth_issues": ["none"],
    "ground_truth_severity": "low",
    "required_keywords": [],
    "critical_module": False,
}

BUG_CODE = {
    "ground_truth_issues": ["bug"],
    "ground_truth_severity": "high",
    "required_keywords": ["null pointer", "null check"],
    "critical_module": False,
}

SECURITY_CODE = {
    "ground_truth_issues": ["security"],
    "ground_truth_severity": "critical",
    "required_keywords": ["sql injection", "parameterized"],
    "critical_module": True,
}

MULTI_CODE = {
    "ground_truth_issues": ["security", "performance"],
    "ground_truth_severity": "critical",
    "required_keywords": ["sql injection", "nested loop", "parameterized", "o(n^2)"],
    "critical_module": True,
}


def assert_open_interval(score: float) -> None:
    assert 0.0 < score < 1.0, f"expected open interval score, got {score}"


class TestDetectionGrader:
    def test_exact_match_stays_open_interval(self):
        action = Action(action_type="detect", issue_types=[IssueType.BUG])
        score, info = grade_detection(action, BUG_CODE)
        assert_open_interval(score)
        assert score > 0.85
        assert info["task_complete"] is True

    def test_wrong_guess_is_low_but_not_zero(self):
        action = Action(action_type="detect", issue_types=[IssueType.STYLE])
        score, info = grade_detection(action, BUG_CODE)
        assert_open_interval(score)
        assert score < 0.25
        assert info["task_complete"] is False

    def test_partial_multi_issue_gets_midrange_reward(self):
        action = Action(action_type="detect", issue_types=[IssueType.SECURITY])
        score, _ = grade_detection(action, MULTI_CODE)
        assert 0.4 < score < 0.8


class TestSeverityGrader:
    def test_exact_match_clears_medium_success_threshold(self):
        action = Action(action_type="classify", severity=Severity.HIGH)
        score, info = grade_severity(action, BUG_CODE, {})
        assert_open_interval(score)
        assert score > MEDIUM_TASK["success_threshold"]
        assert info["task_complete"] is True

    def test_critical_underclassification_is_penalized(self):
        action = Action(action_type="classify", severity=Severity.MEDIUM)
        score, info = grade_severity(action, SECURITY_CODE, {})
        assert_open_interval(score)
        assert score < 0.5
        assert info["distance"] == 2

    def test_medium_detect_step_unlocks_bonus(self):
        state = {"task": "medium", "code": SECURITY_CODE}
        detect_action = Action(action_type="detect", issue_types=[IssueType.SECURITY])
        classify_action = Action(action_type="classify", severity=Severity.CRITICAL)
        prep_score, prep_info = grade_action(detect_action, state)
        final_score, final_info = grade_action(classify_action, state)
        assert_open_interval(prep_score)
        assert prep_info["task_complete"] is False
        assert final_info["used_detection_bonus"] is True
        assert final_score > 0.9


class TestHardPipeline:
    def test_detect_and_classify_steps_are_valid_in_hard_mode(self):
        state = {"task": "hard", "code": MULTI_CODE, "history": []}
        detect_action = Action(
            action_type="detect",
            issue_types=[IssueType.SECURITY, IssueType.PERFORMANCE],
        )
        classify_action = Action(action_type="classify", severity=Severity.CRITICAL)

        detect_score, detect_info = grade_action(detect_action, state)
        classify_score, classify_info = grade_action(classify_action, state)

        assert_open_interval(detect_score)
        assert_open_interval(classify_score)
        assert detect_info["stage"] == "detect"
        assert classify_info["stage"] == "classify"
        assert detect_info["task_complete"] is False
        assert classify_info["task_complete"] is False

    def test_good_review_scores_above_hard_threshold(self):
        state = {
            "task": "hard",
            "code": SECURITY_CODE,
            "history": [],
            "hard_progress": {
                "detected_issues": ["security"],
                "detect_exact": True,
                "classified_severity": "critical",
                "classify_exact": True,
            },
        }
        comment = (
            "This is a critical security issue caused by SQL injection in the query construction. "
            "I recommend replacing the string concatenation with a parameterized query or prepared "
            "statement so user input is never executed directly. Please fix this before merging."
        )
        action = Action(action_type="review", comment=comment)
        score, info = grade_full_review(action, SECURITY_CODE, state)
        assert_open_interval(score)
        assert score > HARD_TASK["success_threshold"]
        assert info["task_complete"] is True

    def test_keyword_stuffing_is_capped_but_not_zero(self):
        action = Action(
            action_type="review",
            comment="bug security performance style none critical high fix recommend suggest consider",
        )
        score, info = grade_full_review(action, SECURITY_CODE, {"task": "hard", "code": SECURITY_CODE})
        assert_open_interval(score)
        assert score < 0.2
        assert "keyword stuffing" in info["reason"]


class TestConfigContracts:
    @pytest.mark.parametrize("task_config", [EASY_TASK, MEDIUM_TASK, HARD_TASK])
    def test_success_thresholds_stay_in_open_interval(self, task_config):
        assert 0.0 < task_config["success_threshold"] < 1.0

    def test_public_task_numbers_never_use_zero_or_one(self):
        numeric_values = []

        def collect_numbers(value):
            if isinstance(value, dict):
                for child in value.values():
                    collect_numbers(child)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_values.append(float(value))

        collect_numbers(EASY_TASK)
        collect_numbers(MEDIUM_TASK)
        collect_numbers(HARD_TASK)

        for value in numeric_values:
            assert value != 0.0
            assert value != 1.0


class TestGlobalBounds:
    def test_normalized_bounds_are_strict(self):
        assert 0.0 < MIN_SCORE < 1.0
        assert 0.0 < MAX_SCORE < 1.0
        assert MIN_SCORE < MAX_SCORE

    def test_all_grader_paths_stay_in_open_interval(self):
        states = [
            {"task": "easy", "code": BUG_CODE},
            {"task": "medium", "code": SECURITY_CODE},
            {"task": "hard", "code": MULTI_CODE, "history": []},
        ]
        actions = [
            Action(action_type="detect", issue_types=[IssueType.BUG]),
            Action(action_type="detect", issue_types=[IssueType.SECURITY]),
            Action(action_type="classify", severity=Severity.HIGH),
            Action(action_type="classify", severity=Severity.CRITICAL),
            Action(
                action_type="review",
                comment=(
                    "This is a critical security issue caused by SQL injection. "
                    "I recommend parameterized queries and a prepared statement."
                ),
            ),
            Action(action_type="review", comment="bug security performance style none"),
        ]

        for state in states:
            for action in actions:
                score, _ = grade_action(action, dict(state))
                assert_open_interval(score)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
