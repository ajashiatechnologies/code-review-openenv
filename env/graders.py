from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

# Very small EPS to ensure strictly (0, 1) — safe for strict validators
EPS = 1e-6


def normalize_score(score: float) -> float:
    """Force score into strictly open interval (0, 1). Never returns 0.0 or 1.0."""
    score = float(score)
    if score <= 0.0:
        return EPS
    if score >= 1.0:
        return 1.0 - EPS
    return max(EPS, min(1.0 - EPS, score))


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state["code"]

    if task == "easy":
        reward, info = grade_detection(action, code)
    elif task == "medium":
        reward, info = grade_severity(action, code, state)
    elif task == "hard":
        reward, info = grade_full_review(action, code, state)
    else:
        reward, info = 0.05, {"reason": "unknown task"}

    # ALWAYS normalize at the final step
    reward = normalize_score(reward)
    return reward, info


# ── EASY TASK ──────────────────────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect" or not action.issue_types:
        return 0.05, {"reason": "wrong action type or missing issue_types"}

    predicted = set(it.value for it in action.issue_types)
    correct = set(code["ground_truth_issues"])

    if "none" in correct and predicted != {"none"}:
        return 0.05, {"reason": "false positive", "task_complete": False}

    if "none" in correct and predicted == {"none"}:
        return 0.95, {"task_complete": True, "reason": "correct: no issue"}

    if "none" in predicted and "none" not in correct:
        return 0.05, {"reason": "false negative", "task_complete": False}

    if len(predicted) >= len(ALL_ISSUE_WORDS) - 1:
        return 0.10, {"reason": "keyword stuffing"}

    intersection = predicted & correct
    union = predicted | correct

    if intersection == correct and predicted == correct:
        return 0.95, {"task_complete": True, "reason": "exact match"}

    if intersection:
        jaccard = len(intersection) / len(union)
        score = 0.4 + jaccard * 0.5
        return score, {"task_complete": False, "reason": "partial match"}

    return 0.05, {"task_complete": False, "reason": "no correct issue detected"}


# ── MEDIUM TASK ────────────────────────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return 0.05, {"reason": "wrong action type"}

    correct = code["ground_truth_severity"]
    predicted = action.severity.value

    c_idx = SEVERITY_ORDER.index(correct)
    p_idx = SEVERITY_ORDER.index(predicted)
    dist = abs(c_idx - p_idx)

    score = 0.90 - dist * 0.20

    # Penalty for under-classifying critical modules
    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.15

    # Bonus for prior correct detection
    history = state.get("history", [])
    if any("detect" in h and "task_complete=True" in h for h in history):
        score += 0.05

    return score, {
        "task_complete": dist == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": dist,
    }


# ── HARD TASK ──────────────────────────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "review" or not action.comment:
        return 0.05, {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.0
    correct_issues = code["ground_truth_issues"]
    word_count = len(comment.split())

    # Anti-stuffing check
    if word_count > 0:
        issue_word_hits = sum(1 for w in ALL_ISSUE_WORDS if w in comment)
        if (issue_word_hits / word_count) > 0.15:
            return 0.05, {"reason": "keyword stuffing"}

    # Preparation bonus
    history = state.get("history", [])
    detected = any("detect" in h for h in history)
    classified = any("classify" in h for h in history)

    if detected and classified:
        score += 0.15
    elif detected or classified:
        score += 0.07

    # Word count bonus
    if word_count >= 60:
        score += 0.10
    elif word_count >= 30:
        score += 0.05

    # Issue mention scoring
    if "none" not in correct_issues:
        matched = [iss for iss in correct_issues if iss in comment]
        score += (len(matched) / max(len(correct_issues), 1)) * 0.20

    # Severity mention bonus
    if code["ground_truth_severity"] in comment:
        score += 0.10

    # Required keywords
    keywords = code.get("required_keywords", [])
    if keywords:
        kw_hits = sum(1 for k in keywords if k.lower() in comment)
        score += (kw_hits / len(keywords)) * 0.20

    # Fix suggestion bonus
    if any(w in comment for w in ["fix", "replace", "avoid", "refactor", "validate"]):
        score += 0.15

    # Tone bonus
    if any(w in comment for w in ["suggest", "recommend", "consider"]):
        score += 0.10

    # False positive penalty
    if "none" in correct_issues:
        score -= 0.20

    return score, {
        "task_complete": score >= 0.55,
        "word_count": word_count,
    }
