from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

EPS = 0.01  # Strictly (0, 1) — safe margin for validator


def normalize_score(score: float) -> float:
    """Clamp score to strictly open interval (0, 1). Never returns 0.0 or 1.0."""
    return max(EPS, min(1.0 - EPS, float(score)))


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state["code"]

    if task == "easy":
        return grade_detection(action, code)
    elif task == "medium":
        return grade_severity(action, code, state)
    elif task == "hard":
        return grade_full_review(action, code, state)

    return normalize_score(0.05), {"reason": "unknown task"}


# ── EASY ──────────────────────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:

    if action.action_type != "detect" or not action.issue_types:
        return normalize_score(0.05), {"reason": "wrong action type or missing issue_types"}

    predicted = set(it.value for it in action.issue_types)
    correct = set(code["ground_truth_issues"])

    if "none" in correct and predicted != {"none"}:
        return normalize_score(0.05), {"reason": "false positive", "task_complete": False}

    if "none" in correct and predicted == {"none"}:
        return normalize_score(0.95), {"task_complete": True, "reason": "correct: no issue"}

    if "none" in predicted and "none" not in correct:
        return normalize_score(0.05), {"reason": "false negative", "task_complete": False}

    if len(predicted) >= len(ALL_ISSUE_WORDS) - 1:
        return normalize_score(0.10), {"reason": "keyword stuffing"}

    intersection = predicted & correct
    union = predicted | correct

    if intersection == correct and predicted == correct:
        return normalize_score(0.95), {"task_complete": True, "reason": "exact match"}

    if intersection:
        jaccard = len(intersection) / len(union)
        score = 0.4 + jaccard * 0.5
        return normalize_score(score), {
            "task_complete": False,
            "reason": "partial match",
        }

    return normalize_score(0.05), {"task_complete": False, "reason": "no correct issue detected"}


# ── MEDIUM ───────────────────────────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:

    if action.action_type != "classify" or action.severity is None:
        return normalize_score(0.05), {"reason": "wrong action type"}

    correct = code["ground_truth_severity"]
    predicted = action.severity.value

    c_idx = SEVERITY_ORDER.index(correct)
    p_idx = SEVERITY_ORDER.index(predicted)
    dist = abs(c_idx - p_idx)

    # Base score — max is 0.90 (never reaches 1.0 naturally)
    score = 0.90 - dist * 0.20

    # Penalty for under-classifying critical modules
    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.15

    # Bonus for prior correct detection (applied before normalize)
    history = state.get("history", [])
    if any("detect" in h and "task_complete=True" in h for h in history):
        score += 0.05

    # Normalize last — after all adjustments
    score = normalize_score(score)

    return score, {
        "task_complete": dist == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": dist,
    }


# ── HARD ───────────────────────────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:

    if action.action_type != "review" or not action.comment:
        return normalize_score(0.05), {"reason": "invalid review action"}

    comment = action.comment.lower()
    score = 0.0
    correct_issues = code["ground_truth_issues"]
    word_count = len(comment.split())

    # Anti-stuffing: reject if issue keywords dominate the comment
    if word_count > 0:
        issue_word_hits = sum(1 for w in ALL_ISSUE_WORDS if w in comment)
        if (issue_word_hits / word_count) > 0.15:
            return normalize_score(0.05), {"reason": "keyword stuffing"}

    # Preparation bonus: reward prior detect/classify steps
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

    # Required keywords scoring
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

    # False positive penalty (comment flagged issues when there are none)
    if "none" in correct_issues:
        score -= 0.20

    # Normalize last — after all adjustments
    score = normalize_score(score)

    return score, {
        "task_complete": score >= 0.55,
        "word_count": word_count,
    }