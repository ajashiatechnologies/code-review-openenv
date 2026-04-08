from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

EPS = 1e-9   # Even smaller for ultra-strict validators


def normalize_score(score: float) -> float:
    """Ultra-strict normalization: ALWAYS returns value strictly in (0, 1)"""
    score = float(score)
    if score <= 0.0:
        return EPS
    if score >= 1.0:
        return 1.0 - EPS
    # Add extra safety layer
    return max(EPS, min(1.0 - EPS, score))


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
        reward, info = 0.1, {"reason": "unknown task"}

    # FINAL SAFETY NET - normalize every single time
    reward = normalize_score(reward)
    return reward, info


# EASY
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return 0.05, {"reason": "wrong action type or missing issue_types"}

    predicted = set(it.value for it in action.issue_types if it)
    correct = set(code.get("ground_truth_issues", []))

    if "none" in correct:
        if predicted == {"none"}:
            return 0.95, {"task_complete": True, "reason": "correct: no issue"}
        else:
            return 0.05, {"reason": "false positive", "task_complete": False}

    if "none" in predicted:
        return 0.05, {"reason": "false negative", "task_complete": False}

    if len(predicted) > 4:  # too many issues = stuffing
        return 0.10, {"reason": "keyword stuffing"}

    intersection = predicted & correct
    union = predicted | correct

    if predicted == correct:
        return 0.95, {"task_complete": True, "reason": "exact match"}

    if intersection:
        jaccard = len(intersection) / max(len(union), 1)
        score = 0.4 + jaccard * 0.55
        return score, {"task_complete": False, "reason": "partial match"}

    return 0.05, {"task_complete": False, "reason": "no match"}


# MEDIUM
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return 0.05, {"reason": "wrong action type"}

    correct = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value

    c_idx = SEVERITY_ORDER.index(correct)
    p_idx = SEVERITY_ORDER.index(predicted)
    dist = abs(c_idx - p_idx)

    score = 0.85 - (dist * 0.22)

    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.18

    # Prior detection bonus
    history = state.get("history", [])
    if any("detect" in h and "task_complete=True" in str(h) for h in history):
        score += 0.08

    return score, {
        "task_complete": dist == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": dist,
    }


# HARD
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return 0.05, {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.0
    correct_issues = code.get("ground_truth_issues", [])
    word_count = len(comment.split())

    # Anti-stuffing
    if word_count > 0:
        issue_hits = sum(1 for w in ALL_ISSUE_WORDS if w in comment)
        if issue_hits / word_count > 0.18:
            return 0.05, {"reason": "keyword stuffing"}

    # Bonuses
    history = state.get("history", [])
    if any("detect" in h for h in history) and any("classify" in h for h in history):
        score += 0.18
    elif any("detect" in h for h in history) or any("classify" in h for h in history):
        score += 0.08

    if word_count >= 50:
        score += 0.12
    elif word_count >= 25:
        score += 0.06

    if "none" not in correct_issues:
        matched = sum(1 for iss in correct_issues if iss in comment)
        score += (matched / max(len(correct_issues), 1)) * 0.25

    if code.get("ground_truth_severity") in comment:
        score += 0.12

    if any(w in comment for w in ["fix", "refactor", "suggest", "recommend", "avoid"]):
        score += 0.15

    if "none" in correct_issues:
        score = max(0.0, score - 0.25)

    return score, {
        "task_complete": score >= 0.50,
        "word_count": word_count,
    }
