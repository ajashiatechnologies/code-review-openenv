import math
from typing import Any, Dict, Tuple

from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}

MIN_SCORE = 0.02
MAX_SCORE = 0.98
MID_SCORE = 0.50


def normalize_score(score: float) -> float:
    """Force every score into the strict open interval (0, 1)."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return MID_SCORE

    if not math.isfinite(value):
        return MID_SCORE

    return max(MIN_SCORE, min(MAX_SCORE, value))


def _issue_values(action: Action) -> set[str]:
    values = {item.value for item in (action.issue_types or []) if item}
    if "none" in values and len(values) > 1:
        values.discard("none")
    return values


def _detection_score(predicted: set[str], correct: set[str]) -> tuple[float, Dict[str, Any]]:
    if not predicted:
        return 0.18, {"reason": "missing issue types", "task_complete": False}

    if correct == {"none"}:
        if predicted == {"none"}:
            return 0.90, {"reason": "correctly identified clean code", "task_complete": True}
        return 0.14, {"reason": "false positive on clean code", "task_complete": False}

    if predicted == {"none"}:
        return 0.12, {"reason": "false negative", "task_complete": False}

    if predicted == correct:
        return 0.92, {"reason": "exact match", "task_complete": True}

    intersection = predicted & correct
    if not intersection:
        return 0.16, {"reason": "no match", "task_complete": False}

    union = predicted | correct
    jaccard = len(intersection) / max(len(union), 1)
    precision = len(intersection) / max(len(predicted), 1)
    recall = len(intersection) / max(len(correct), 1)
    score = 0.28 + (0.34 * jaccard) + (0.18 * precision) + (0.12 * recall)
    return score, {
        "reason": "partial match",
        "task_complete": False,
        "matched": sorted(intersection),
        "missed": sorted(correct - predicted),
        "extra": sorted(predicted - correct),
    }


def _severity_core(
    predicted: str,
    correct: str,
    *,
    critical_module: bool,
    prior_detection_bonus: bool = False,
) -> tuple[float, int]:
    distance = abs(SEVERITY_ORDER.index(correct) - SEVERITY_ORDER.index(predicted))
    base_scores = {0: 0.90, 1: 0.72, 2: 0.46, 3: 0.20}
    score = base_scores[distance]

    if critical_module and SEVERITY_ORDER.index(predicted) < SEVERITY_ORDER.index(correct):
        score -= 0.08

    if prior_detection_bonus:
        score += 0.04

    return score, distance


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state.get("code", {})

    if task == "easy":
        reward, info = grade_detection(action, code)
    elif task == "medium":
        reward, info = grade_medium_task(action, code, state)
    elif task == "hard":
        reward, info = grade_full_review(action, code, state)
    else:
        reward, info = MID_SCORE, {"reason": "unknown task"}

    return normalize_score(reward), info


def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "detect":
        return normalize_score(0.18), {"reason": "invalid detect action", "task_complete": False}

    predicted = _issue_values(action)
    correct = set(code.get("ground_truth_issues", []))
    score, info = _detection_score(predicted, correct)
    return normalize_score(score), info


def grade_medium_task(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type == "detect":
        detect_score, detect_info = grade_detection(action, code)
        state["medium_detect_exact"] = bool(detect_info.get("task_complete", False))
        state["medium_detect_issues"] = sorted(_issue_values(action))
        prep_score = 0.18 + ((detect_score - MIN_SCORE) * 0.45)
        return normalize_score(prep_score), {
            **detect_info,
            "task_complete": False,
            "stage": "detect",
            "reason": "medium prep: detection recorded",
        }

    return grade_severity(action, code, state)


def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    if action.action_type != "classify" or action.severity is None:
        return normalize_score(0.18), {"reason": "invalid classify action", "task_complete": False}

    correct = code.get("ground_truth_severity", "medium")
    predicted = action.severity.value
    score, distance = _severity_core(
        predicted,
        correct,
        critical_module=bool(code.get("critical_module")),
        prior_detection_bonus=bool(state.get("medium_detect_exact")),
    )

    return normalize_score(score), {
        "task_complete": distance == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": distance,
        "used_detection_bonus": bool(state.get("medium_detect_exact")),
    }


def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    progress = state.setdefault(
        "hard_progress",
        {
            "detected_issues": [],
            "detect_exact": False,
            "classified_severity": None,
            "classify_exact": False,
        },
    )

    if action.action_type == "detect":
        predicted = _issue_values(action)
        correct = set(code.get("ground_truth_issues", []))
        detect_score, detect_info = _detection_score(predicted, correct)
        progress["detected_issues"] = sorted(predicted)
        progress["detect_exact"] = bool(detect_info.get("task_complete", False))
        stage_score = 0.18 + ((normalize_score(detect_score) - MIN_SCORE) * 0.45)
        return normalize_score(stage_score), {
            **detect_info,
            "task_complete": False,
            "stage": "detect",
        }

    if action.action_type == "classify" and action.severity is not None:
        correct_severity = code.get("ground_truth_severity", "medium")
        predicted = action.severity.value
        score, distance = _severity_core(
            predicted,
            correct_severity,
            critical_module=bool(code.get("critical_module")),
            prior_detection_bonus=bool(progress.get("detect_exact")),
        )
        progress["classified_severity"] = predicted
        progress["classify_exact"] = distance == 0
        stage_score = 0.20 + ((normalize_score(score) - MIN_SCORE) * 0.55)
        return normalize_score(stage_score), {
            "task_complete": False,
            "stage": "classify",
            "correct_severity": correct_severity,
            "predicted": predicted,
            "distance": distance,
        }

    if action.action_type != "review" or not action.comment:
        return normalize_score(0.18), {"reason": "review step requires a comment", "task_complete": False}

    comment = action.comment.lower()
    words = comment.split()
    word_count = len(words)
    correct_issues = code.get("ground_truth_issues", [])
    required_keywords = [keyword.lower() for keyword in code.get("required_keywords", [])]

    label_hits = sum(1 for label in ALL_ISSUE_WORDS if label in comment)
    if word_count > 0 and (label_hits / word_count) > 0.18:
        return normalize_score(0.16), {
            "reason": "keyword stuffing detected",
            "task_complete": False,
            "word_count": word_count,
        }

    score = 0.18
    breakdown: Dict[str, float] = {"base": 0.18}

    if progress.get("detect_exact") and progress.get("classify_exact"):
        score += 0.07
        breakdown["preparation"] = 0.07
    elif progress.get("detect_exact") or progress.get("classify_exact"):
        score += 0.04
        breakdown["preparation"] = 0.04

    if word_count >= 60:
        score += 0.10
        breakdown["word_count"] = 0.10
    elif word_count >= 35:
        score += 0.06
        breakdown["word_count"] = 0.06

    real_issues = [issue for issue in correct_issues if issue != "none"]
    if real_issues:
        issue_hits = sum(1 for issue in real_issues if issue in comment)
        issue_score = (issue_hits / len(real_issues)) * 0.20
        score += issue_score
        breakdown["issue_mention"] = round(issue_score, 4)
    else:
        if any(phrase in comment for phrase in ["no issue", "looks good", "clean", "safe to merge"]):
            score += 0.20
            breakdown["issue_mention"] = 0.20

    severity = code.get("ground_truth_severity", "")
    if severity and severity in comment:
        score += 0.10
        breakdown["severity"] = 0.10

    if required_keywords:
        keyword_hits = sum(1 for keyword in required_keywords if keyword in comment)
        keyword_score = (keyword_hits / len(required_keywords)) * 0.15
        score += keyword_score
        breakdown["keywords"] = round(keyword_score, 4)

    fix_phrases = [
        "replace",
        "refactor",
        "use parameterized",
        "prepared statement",
        "sanitize",
        "avoid",
        "validate",
        "use a guard",
        "handle the error",
    ]
    if any(phrase in comment for phrase in fix_phrases):
        score += 0.10
        breakdown["fix"] = 0.10

    tone_phrases = ["recommend", "suggest", "consider", "please", "should"]
    if any(phrase in comment for phrase in tone_phrases):
        score += 0.08
        breakdown["tone"] = 0.08

    if correct_issues == ["none"] and any(label in comment for label in ALL_ISSUE_WORDS - {"none"}):
        score -= 0.12
        breakdown["false_positive_penalty"] = -0.12

    final_score = normalize_score(score)
    return final_score, {
        "task_complete": final_score >= 0.55,
        "stage": "review",
        "score_breakdown": breakdown,
        "word_count": word_count,
        "detected_issues": progress.get("detected_issues", []),
        "classified_severity": progress.get("classified_severity"),
    }
