from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

EPS = 0.07


def normalize_score(score: float) -> float:
    """Maximum safety - every reward is forced between 0.07 and 0.85"""
    score = float(score)
    
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

    if task == "easy":
        reward, info = grade_detection(action, code)
    elif task == "medium":
        reward, info = grade_severity(action, code, state)
    elif task == "hard":
        reward, info = grade_full_review(action, code, state)
    else:
        reward, info = 0.5, {"reason": "unknown task"}

    # This is the most important line - applied to EVERY return
    reward = normalize_score(reward)
    return reward, info


def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return normalize_score(0.30), {"reason": "invalid detect action"}

    predicted = {it.value for it in action.issue_types if it}
    correct = set(code.get("ground_truth_issues", []))

    if predicted == correct and correct:
        return normalize_score(0.85), {"task_complete": True, "reason": "exact match"}

    if "none" in correct:
        return normalize_score(0.85 if predicted == {"none"} else 0.25), {"task_complete": predicted == {"none"}}

    if "none" in predicted:
        return normalize_score(0.25), {"reason": "false negative"}

    intersection = predicted & correct
    if intersection:
        jaccard = len(intersection) / max(len(predicted | correct), 1)
        score = 0.45 + jaccard * 0.40
        return normalize_score(score), {"reason": "partial match"}

    return normalize_score(0.30), {"reason": "no match"}


def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return normalize_score(0.40), {"reason": "invalid classify action"}

    correct = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value

    dist = abs(SEVERITY_ORDER.index(correct) - SEVERITY_ORDER.index(predicted))
    score = 0.78 - (dist * 0.18)

    if code.get("critical_module") and SEVERITY_ORDER.index(predicted) < SEVERITY_ORDER.index(correct):
        score -= 0.08

    return normalize_score(score), {"task_complete": dist == 0}


def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return normalize_score(0.35), {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.45

    word_count = len(comment.split())
    correct_issues = code.get("ground_truth_issues", [])

    if word_count >= 40:
        score += 0.15
    elif word_count >= 20:
        score += 0.08

    if any(iss in comment for iss in correct_issues if iss != "none"):
        score += 0.15

    if code.get("ground_truth_severity") in comment:
        score += 0.10

    if any(w in comment for w in ["fix", "refactor", "suggest", "recommend", "avoid", "improve", "consider"]):
        score += 0.12

    if "none" in correct_issues:
        score = max(0.35, score - 0.10)

    return normalize_score(score), {"task_complete": score >= 0.55}