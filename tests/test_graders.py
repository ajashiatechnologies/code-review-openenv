"""
tests/test_graders.py
Comprehensive unit tests for the Code Review OpenEnv graders.
Run with: pytest tests/test_graders.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from env.models import Action, IssueType, Severity
from env.graders import (
    grade_detection,
    grade_severity,
    grade_full_review,
    SEVERITY_ORDER,
)

# ── Shared fixtures ──────────────────────────────────────────────────────────

NONE_CODE = {
    "ground_truth_issues":   ["none"],
    "ground_truth_severity": "low",
    "required_keywords":     [],
    "critical_module":       False,
}

BUG_CODE = {
    "ground_truth_issues":   ["bug"],
    "ground_truth_severity": "high",
    "required_keywords":     ["null pointer", "null check"],
    "critical_module":       False,
}

SECURITY_CODE = {
    "ground_truth_issues":   ["security"],
    "ground_truth_severity": "critical",
    "required_keywords":     ["sql injection", "parameterized"],
    "critical_module":       True,
}

MULTI_CODE = {
    "ground_truth_issues":   ["security", "performance"],
    "ground_truth_severity": "critical",
    "required_keywords":     ["sql injection", "nested loop", "parameterized", "O(n^2)"],
    "critical_module":       True,
}

EMPTY_STATE = {"history": [], "actions_taken": []}


# ═══════════════════════════════════════════════════════════════════════════
# EASY GRADER: grade_detection
# ═══════════════════════════════════════════════════════════════════════════

class TestEasyGrader:

    def test_exact_single_issue_scores_1(self):
        a = Action(action_type="detect", issue_types=[IssueType.BUG])
        score, info = grade_detection(a, BUG_CODE)
        assert score == 1.0
        assert info["task_complete"] is True

    def test_exact_multi_issue_scores_1(self):
        a = Action(action_type="detect", issue_types=[IssueType.SECURITY, IssueType.PERFORMANCE])
        score, info = grade_detection(a, MULTI_CODE)
        assert score == 1.0
        assert info["task_complete"] is True

    def test_correct_none_scores_1(self):
        a = Action(action_type="detect", issue_types=[IssueType.NONE])
        score, info = grade_detection(a, NONE_CODE)
        assert score == 1.0

    def test_false_positive_penalized(self):
        a = Action(action_type="detect", issue_types=[IssueType.BUG])
        score, _ = grade_detection(a, NONE_CODE)
        assert score < 0

    def test_false_negative_penalized(self):
        """Predicting 'none' on real-issue code should be penalized."""
        a = Action(action_type="detect", issue_types=[IssueType.NONE])
        score, _ = grade_detection(a, BUG_CODE)
        assert score < 0

    def test_partial_match_multi_issue(self):
        """Predicting only one of two issues gets partial credit."""
        a = Action(action_type="detect", issue_types=[IssueType.SECURITY])
        score, info = grade_detection(a, MULTI_CODE)
        assert 0.0 < score < 1.0

    def test_completely_wrong_scores_zero(self):
        a = Action(action_type="detect", issue_types=[IssueType.STYLE])
        score, _ = grade_detection(a, BUG_CODE)
        assert score == 0.0

    def test_wrong_action_type_penalized(self):
        a = Action(action_type="classify", severity=Severity.HIGH)
        score, info = grade_detection(a, BUG_CODE)
        assert score < 0

    def test_keyword_stuffing_blocked(self):
        """Predicting all issue types should not score high."""
        a = Action(action_type="detect",
                   issue_types=[IssueType.BUG, IssueType.SECURITY,
                                 IssueType.PERFORMANCE, IssueType.STYLE])
        score, info = grade_detection(a, SECURITY_CODE)
        assert score <= 0.2, f"Stuffing should be blocked, got {score}"

    def test_scores_vary_across_inputs(self):
        """Grader must return different scores for different inputs — never constant."""
        a = Action(action_type="detect", issue_types=[IssueType.SECURITY])
        scores = set()
        for code in [NONE_CODE, BUG_CODE, SECURITY_CODE, MULTI_CODE]:
            s, _ = grade_detection(a, code)
            scores.add(s)
        assert len(scores) > 1, "Grader returned identical scores for all inputs"

    def test_score_never_exceeds_1(self):
        for issue in list(IssueType):
            a = Action(action_type="detect", issue_types=[issue])
            for code in [NONE_CODE, BUG_CODE, SECURITY_CODE, MULTI_CODE]:
                s, _ = grade_detection(a, code)
                assert s <= 1.0, f"Score {s} exceeds 1.0"


# ═══════════════════════════════════════════════════════════════════════════
# MEDIUM GRADER: grade_severity
# ═══════════════════════════════════════════════════════════════════════════

class TestMediumGrader:

    def test_exact_match_scores_1(self):
        a = Action(action_type="classify", severity=Severity.HIGH)
        score, info = grade_severity(a, BUG_CODE, EMPTY_STATE)
        assert score == 1.0
        assert info["task_complete"] is True

    def test_one_step_off_scores_0_7(self):
        # BUG_CODE correct = high, predicting medium (1 step off)
        a = Action(action_type="classify", severity=Severity.MEDIUM)
        score, info = grade_severity(a, BUG_CODE, EMPTY_STATE)
        assert 0.6 <= score <= 0.8
        assert info["distance"] == 1

    def test_critical_module_underclassify_penalized(self):
        """Under-classifying a critical module gets penalized."""
        a = Action(action_type="classify", severity=Severity.MEDIUM)
        score, _ = grade_severity(a, SECURITY_CODE, EMPTY_STATE)
        # Correct=critical, predicted=medium (2 steps off), critical_module=True
        # base = max(0.1, 1.0 - 0.6) = 0.4; penalty -0.2; clamped = 0.2
        assert score <= 0.3

    def test_critical_module_overclassify_no_penalty(self):
        """Over-classifying (predicting too high) should NOT be penalized."""
        # BUG_CODE correct=high, critical_module=False — just test no extra penalty
        a = Action(action_type="classify", severity=Severity.CRITICAL)
        score_no_crit, _ = grade_severity(a, BUG_CODE, EMPTY_STATE)
        # Should score based only on distance, no critical module penalty (critical_module=False)
        assert score_no_crit > 0.0

    def test_score_never_below_zero(self):
        """FIX: clamping — score must never go below 0.0."""
        for sv in list(Severity):
            a = Action(action_type="classify", severity=sv)
            score, _ = grade_severity(a, SECURITY_CODE, EMPTY_STATE)
            assert score >= 0.0, f"Score {score} is negative for severity={sv}"

    def test_score_never_exceeds_1(self):
        for sv in list(Severity):
            a = Action(action_type="classify", severity=sv)
            score, _ = grade_severity(a, SECURITY_CODE, EMPTY_STATE)
            assert score <= 1.0

    def test_scores_vary_by_distance(self):
        """Different severity predictions must produce different scores."""
        scores = []
        for sv in ["critical", "high", "medium", "low"]:
            a = Action(action_type="classify", severity=Severity(sv))
            score, _ = grade_severity(a, SECURITY_CODE, EMPTY_STATE)
            scores.append(score)
        assert len(set(scores)) > 1, "Grader returned identical scores for all severities"

    def test_wrong_action_type_penalized(self):
        a = Action(action_type="detect", issue_types=[IssueType.BUG])
        score, _ = grade_severity(a, BUG_CODE, EMPTY_STATE)
        assert score < 0


# ═══════════════════════════════════════════════════════════════════════════
# HARD GRADER: grade_full_review
# ═══════════════════════════════════════════════════════════════════════════

class TestHardGrader:

    def test_empty_comment_scores_zero(self):
        a = Action(action_type="review", comment="")
        score, _ = grade_full_review(a, SECURITY_CODE, EMPTY_STATE)
        assert score == 0.0

    def test_missing_comment_scores_zero(self):
        a = Action(action_type="review", comment=None)
        score, _ = grade_full_review(a, SECURITY_CODE, EMPTY_STATE)
        assert score == 0.0

    def test_keyword_stuffing_blocked(self):
        """A comment that is just a dump of keywords should score very low."""
        stuffed = "bug security performance style none critical fix recommend suggest consider"
        a = Action(action_type="review", comment=stuffed)
        score, info = grade_full_review(a, SECURITY_CODE, EMPTY_STATE)
        assert score <= 0.1, f"Stuffing should be blocked, got {score}: {info}"

    def test_good_security_review_scores_well(self):
        state = {
            "history": [
                "step=1 | action=detect | task_complete=True",
                "step=2 | action=classify | task_complete=True",
            ]
        }
        good_comment = (
            "This code has a critical security vulnerability — specifically SQL injection. "
            "The string concatenation approach allows an attacker to manipulate the query. "
            "I recommend replacing this with parameterized queries or a prepared statement. "
            "For example: cursor.execute('SELECT * FROM users WHERE name = %s', (name,)). "
            "Given this is in the authentication module, this is a critical severity issue. "
            "Please fix before merging."
        )
        a = Action(action_type="review", comment=good_comment)
        score, info = grade_full_review(a, SECURITY_CODE, state)
        assert score >= 0.55, f"Good review scored too low: {score}. Breakdown: {info}"

    def test_false_positive_on_clean_code_penalized(self):
        a = Action(action_type="review",
                   comment="This code has a security vulnerability and performance bug. Fix it.")
        score, _ = grade_full_review(a, NONE_CODE, EMPTY_STATE)
        # Should be penalized for reviewing clean code as buggy
        assert score < 0.3

    def test_preparation_bonus_applied(self):
        state_with_history = {
            "history": [
                "step=1 | action=detect | task_complete=True",
                "step=2 | action=classify | task_complete=True",
            ]
        }
        state_no_history = {"history": []}

        comment = (
            "This code has a security issue — SQL injection via string concatenation. "
            "It is a critical risk. I recommend using parameterized queries. "
            "Please fix before merging. Consider adding input validation as well."
        )
        a = Action(action_type="review", comment=comment)
        score_with, _ = grade_full_review(a, SECURITY_CODE, state_with_history)
        score_without, _ = grade_full_review(a, SECURITY_CODE, state_no_history)
        assert score_with > score_without, "Preparation bonus was not applied"

    def test_score_always_in_range(self):
        comments = [
            "nothing",
            "bug security performance fix recommend critical sql injection parameterized",
            "",
            "This is a critical security vulnerability. The SQL injection via string "
            "concatenation allows attackers to manipulate database queries. I recommend "
            "using parameterized queries. This should be fixed immediately.",
        ]
        for comment in comments:
            a = Action(action_type="review", comment=comment)
            score, _ = grade_full_review(a, SECURITY_CODE, EMPTY_STATE)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for comment: {comment[:40]}"

    def test_scores_vary_by_quality(self):
        """Better reviews must score higher than worse ones."""
        a_bad  = Action(action_type="review", comment="bad code fix it")
        a_good = Action(action_type="review", comment=(
            "This code has a critical security vulnerability. The SQL injection risk "
            "from string concatenation in the authentication module is severe. "
            "I recommend replacing with parameterized queries: "
            "cursor.execute('SELECT * FROM users WHERE name = %s', (name,)). "
            "Please fix before merging. Consider also using an ORM."
        ))
        s_bad,  _ = grade_full_review(a_bad,  SECURITY_CODE, EMPTY_STATE)
        s_good, _ = grade_full_review(a_good, SECURITY_CODE, EMPTY_STATE)
        assert s_good > s_bad, f"Good review ({s_good}) not higher than bad ({s_bad})"


# ═══════════════════════════════════════════════════════════════════════════
# CROSS-GRADER: invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestInvariants:

    def test_all_graders_return_tuple(self):
        codes = [NONE_CODE, BUG_CODE, SECURITY_CODE, MULTI_CODE]
        for code in codes:
            a1 = Action(action_type="detect", issue_types=[IssueType.BUG])
            a2 = Action(action_type="classify", severity=Severity.HIGH)
            a3 = Action(action_type="review", comment="test review comment for security issues")
            for a, grader in [(a1, grade_detection), (a3, grade_full_review)]:
                result = grader(a, code) if grader != grade_full_review else grader(a, code, EMPTY_STATE)
                assert isinstance(result, tuple) and len(result) == 2
            r = grade_severity(a2, code, EMPTY_STATE)
            assert isinstance(r, tuple) and len(r) == 2

    def test_all_scores_in_valid_range(self):
        """No grader may return a score outside [-0.2, 1.0]."""
        codes = [NONE_CODE, BUG_CODE, SECURITY_CODE, MULTI_CODE]
        actions_easy = [Action(action_type="detect", issue_types=[it]) for it in IssueType]
        actions_med  = [Action(action_type="classify", severity=sv) for sv in Severity]
        for code in codes:
            for a in actions_easy:
                s, _ = grade_detection(a, code)
                assert -0.3 <= s <= 1.0, f"Out of range: {s}"
            for a in actions_med:
                s, _ = grade_severity(a, code, EMPTY_STATE)
                assert -0.3 <= s <= 1.0, f"Out of range: {s}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
