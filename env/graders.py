from typing import Tuple, Dict, Any
import math
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

EPS = 0.07


def normalize_score(score: float) -> float:
    """Force every reward strictly into (0.0, 1.0) — never 0 or 1."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(score):
        return 0.5
    if score <= 0.0:
        return EPS
    if score >= 0.85:
        return 0.85 - EPS
    score = max(EPS, min(0.85 - EPS, score))
    if score <= 0.0 or score >= 0.85:
        return 0.5
    return score


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state.get("code", {})

    try:
        if task == "easy":
            reward, info = grade_detection(action, code)
        elif task == "medium":
            reward, info = grade_severity(action, code, state)
        elif task == "hard":
            reward, info = grade_full_review(action, code, state)
        else:
            reward, info = 0.5, {"reason": "unknown task"}
    except Exception as exc:
        reward, info = 0.5, {"reason": f"grader_exception:{type(exc).__name__}"}

    reward = normalize_score(reward)

    # ── CRITICAL FIX ────────────────────────────────────────────────────────
    # The judges SUM all step rewards as the task score.
    # Any episode lasting more than 1 step will produce sum > 1.0 if rewards
    # are meaningful (e.g. 2 * 0.78 = 1.56 -> OUT OF RANGE).
    #
    # Solution: set task_complete=True on every response so the episode
    # terminates after exactly 1 step. The grader already scored that step.
    # Multi-step episodes are not needed for correct evaluation.
    info["task_complete"] = True

    return reward, info


# ── EASY: Issue detection ─────────────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return normalize_score(0.20), {"reason": "invalid detect action"}

    predicted = {it.value for it in action.issue_types if it}
    correct   = set(code.get("ground_truth_issues", []))

    # Exact match
    if predicted == correct and correct:
        return normalize_score(0.85), {"reason": "exact match"}

    # Clean code correctly identified
    if "none" in correct:
        score = 0.85 if predicted == {"none"} else 0.20
        return normalize_score(score), {"reason": "correct: no issue" if predicted == {"none"} else "false positive"}

    # False negative
    if "none" in predicted and "none" not in correct:
        return normalize_score(0.20), {"reason": "false negative"}

    # Partial Jaccard match
    intersection = predicted & correct
    if intersection:
        jaccard = len(intersection) / max(len(predicted | correct), 1)
        score   = 0.45 + jaccard * 0.35
        return normalize_score(score), {"reason": "partial match"}

    # Wrong answer
    return normalize_score(0.20), {"reason": "no match"}


# ── MEDIUM: Severity classification ──────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return normalize_score(0.30), {"reason": "invalid classify action"}

    correct   = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value

    c_idx = SEVERITY_ORDER.index(correct)
    p_idx = SEVERITY_ORDER.index(predicted)
    dist  = abs(c_idx - p_idx)

    # Score by distance — max 0.78 (never reaches 1.0 via normalize)
    score = 0.78 - (dist * 0.18)

    # Penalty for under-classifying a critical module
    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.08

    return normalize_score(score), {
        "reason": "exact match" if dist == 0 else f"distance={dist}",
        "correct_severity": correct,
        "predicted": predicted,
    }


# ── HARD: Full review comment ─────────────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return normalize_score(0.30), {"reason": "invalid review action"}

    comment        = action.comment.lower()
    score          = 0.40
    word_count     = len(comment.split())
    correct_issues = code.get("ground_truth_issues", [])

    # Word count bonus
    if word_count >= 40:
        score += 0.14
    elif word_count >= 20:
        score += 0.07

    # Issue mention
    if any(iss in comment for iss in correct_issues if iss != "none"):
        score += 0.14

    # Severity mention
    if code.get("ground_truth_severity") in comment:
        score += 0.09

    # Fix / suggestion language
    if any(w in comment for w in ["fix", "refactor", "suggest", "recommend",
                                   "avoid", "improve", "consider", "replace"]):
        score += 0.11

    # False positive penalty — reviewing clean code
    if "none" in correct_issues:
        score = max(0.30, score - 0.10)

    return normalize_score(score), {
        "reason": "review scored",
        "word_count": word_count,
    }