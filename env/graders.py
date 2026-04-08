from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

EPS = 1e-9


def normalize_score(score: float) -> float:
    """Maximum safety normalization for OpenEnv Phase 2 validator"""
    score = float(score)

    if score <= 0.0:
        return EPS
    if score >= 1.0:
        return 1.0 - EPS

    # Double safety clamp
    score = max(EPS, min(1.0 - EPS, score))

    # Absolute fallback
    if score <= 0.0 or score >= 1.0:
        return 0.5

    return score


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state.get("code", {})

    if task == "easy":
        reward, info = grade_detection(action, code)
    elif task == "medium":
        reward, info = grade_severity(action, code, state)
    elif task == "hard":
        reward, info = grade_full_review(action, code, state)
    else:
        reward, info = 0.5, {"reason": "unknown task"}

    # Global final clamp - nothing can escape
    reward = normalize_score(reward)
    return reward, info


# ── EASY ──────────────────────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return 0.25, {"reason": "invalid detect action"}

    predicted = {it.value for it in action.issue_types if it}
    correct = set(code.get("ground_truth_issues", []))

    if predicted == correct and correct:
        return 0.85, {"task_complete": True, "reason": "exact match"}

    if "none" in correct:
        return 0.85 if predicted == {"none"} else 0.15, {"task_complete": predicted == {"none"}}

    if "none" in predicted:
        return 0.15, {"reason": "false negative"}

    intersection = predicted & correct
    if intersection:
        jaccard = len(intersection) / max(len(predicted | correct), 1)
        return 0.4 + jaccard * 0.5, {"reason": "partial match"}

    return 0.2, {"reason": "no match"}


# ── MEDIUM ─────────────────────────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return 0.25, {"reason": "invalid classify action"}

    correct = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value

    dist = abs(SEVERITY_ORDER.index(correct) - SEVERITY_ORDER.index(predicted))
    score = 0.78 - (dist * 0.24)

    if code.get("critical_module") and SEVERITY_ORDER.index(predicted) < SEVERITY_ORDER.index(correct):
        score -= 0.15

    return score, {"task_complete": dist == 0}


# ── HARD ───────────────────────────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return 0.25, {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.3   # safe base score

    word_count = len(comment.split())
    correct_issues = code.get("ground_truth_issues", [])

    if word_count >= 45:
        score += 0.25
    elif word_count >= 25:
        score += 0.15

    if any(iss in comment for iss in correct_issues if iss != "none"):
        score += 0.25

    if code.get("ground_truth_severity") in comment:
        score += 0.15

    if any(w in comment for w in ["fix", "refactor", "suggest", "recommend", "avoid", "improve", "consider"]):
        score += 0.20

    if "none" in correct_issues:
        score = max(0.25, score - 0.1)

    return score, {"task_complete": score >= 0.55}