from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

# Extremely small EPS to satisfy the strictest OpenEnv validator
EPS = 1e-10


def normalize_score(score: float) -> float:
    """Ultra-aggressive normalization - GUARANTEES strictly between 0 and 1"""
    score = float(score)

    if score <= 0.0:
        return EPS
    if score >= 1.0:
        return 1.0 - EPS

    # Double clamp for safety
    score = max(EPS, min(1.0 - EPS, score))

    # Final fallback in case of any floating point weirdness
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

    # FINAL SAFETY NET - normalize every single return
    reward = normalize_score(reward)
    return reward, info


# ── EASY TASK ──────────────────────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return 0.1, {"reason": "invalid detect action"}

    predicted = {it.value for it in action.issue_types if it is not None}
    correct = set(code.get("ground_truth_issues", []))

    if predicted == correct and correct:
        return 0.9, {"task_complete": True, "reason": "exact match"}

    if "none" in correct:
        return 0.05 if predicted != {"none"} else 0.9, {
            "task_complete": predicted == {"none"},
            "reason": "no issue case"
        }

    if "none" in predicted:
        return 0.05, {"reason": "false negative"}

    intersection = predicted & correct
    if intersection:
        jaccard = len(intersection) / max(len(predicted | correct), 1)
        score = 0.35 + (jaccard * 0.6)
        return score, {"reason": "partial match"}

    return 0.05, {"reason": "no match"}


# ── MEDIUM TASK ────────────────────────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return 0.1, {"reason": "invalid classify action"}

    correct = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value

    c_idx = SEVERITY_ORDER.index(correct)
    p_idx = SEVERITY_ORDER.index(predicted)
    dist = abs(c_idx - p_idx)

    score = 0.82 - (dist * 0.23)

    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.18

    # Small bonus for previous correct detection
    history = state.get("history", [])
    if any("detect" in str(h) and "task_complete=True" in str(h) for h in history):
        score += 0.07

    return score, {
        "task_complete": dist == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": dist,
    }


# ── HARD TASK ──────────────────────────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return 0.1, {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.2   # safe starting score

    correct_issues = code.get("ground_truth_issues", [])
    word_count = len(comment.split())

    # Word count bonus
    if word_count >= 50:
        score += 0.25
    elif word_count >= 25:
        score += 0.15

    # Issue mention bonus
    if correct_issues and any(iss in comment for iss in correct_issues):
        score += 0.25

    # Severity mention bonus
    if code.get("ground_truth_severity") in comment:
        score += 0.15

    # Good review language bonus
    if any(w in comment for w in ["suggest", "recommend", "consider", "fix", "refactor", "improve", "avoid"]):
        score += 0.20

    # Penalty if claiming no issues incorrectly
    if "none" in correct_issues and len(comment.split()) < 30:
        score -= 0.15

    return score, {
        "task_complete": score >= 0.55,
        "word_count": word_count,
    }