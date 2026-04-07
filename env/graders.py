from typing import Tuple, Dict, Any
from .models import Action

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

# All valid issue-type words — used to detect keyword stuffing
ALL_ISSUE_WORDS = {"bug", "security", "performance", "style", "none"}


def grade_action(action: Action, state: dict) -> Tuple[float, Dict[str, Any]]:
    task = state.get("task", "easy")
    code = state["code"]

    if task == "easy":
        return grade_detection(action, code)
    elif task == "medium":
        return grade_severity(action, code, state)
    elif task == "hard":
        return grade_full_review(action, code, state)

    return 0.0, {"reason": "unknown task"}


# ── EASY: Detect issue type(s) ──────────────────────────────────────────────
def grade_detection(action: Action, code: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Scoring:
      - Wrong action type          → -0.1
      - False positive (none code) → -0.2
      - Exact full match           →  1.0
      - Partial match (≥1 correct) →  0.5  (for multi-issue)
      - Completely wrong           →  0.0
      - Predicting "none" on real  → -0.1  (FIX: was 0.3 before)
    """
    if action.action_type != "detect" or not action.issue_types:
        return -0.1, {"reason": "wrong action type or missing issue_types"}

    predicted  = set(it.value for it in action.issue_types)
    correct    = set(code["ground_truth_issues"])

    # False positive: agent flags an issue when there is none
    if "none" in correct and predicted != {"none"}:
        return -0.2, {"reason": "false positive — code has no issue", "task_complete": False}

    # Agent correctly identifies clean code
    if "none" in correct and predicted == {"none"}:
        return 1.0, {"task_complete": True, "reason": "correct: no issue"}

    # FIX: agent says "none" on real issue — penalize (was 0.3 before)
    if "none" in predicted and "none" not in correct:
        return -0.1, {"reason": "false negative — missed real issue", "task_complete": False}

    # Anti-keyword-stuffing: penalize if agent predicts all categories
    if len(predicted) >= len(ALL_ISSUE_WORDS) - 1:
        return 0.1, {"reason": "keyword stuffing detected — too many issue types predicted"}

    intersection = predicted & correct
    union        = predicted | correct

    if intersection == correct and predicted == correct:
        # Perfect match
        return 1.0, {"task_complete": True, "reason": "exact match"}

    if intersection:
        # Partial Jaccard-based score: rewards precision AND recall
        jaccard = len(intersection) / len(union)
        score   = round(0.4 + jaccard * 0.5, 2)   # range ~0.4–0.9
        return score, {
            "task_complete": False,
            "reason": "partial match",
            "matched": list(intersection),
            "missed": list(correct - predicted),
            "extra":  list(predicted - correct),
        }

    # Completely wrong
    return 0.0, {"task_complete": False, "reason": "no correct issue detected"}


# ── MEDIUM: Classify severity ───────────────────────────────────────────────
def grade_severity(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Scoring:
      - Wrong action type          → -0.1
      - Exact match                →  1.0
      - 1 step off                 →  0.7
      - 2 steps off                →  0.4
      - 3 steps off                →  0.1
      - Critical module penalty    → -0.2 if critical module under-classified
      - Prior detection bonus      → +0.1 if agent correctly detected issues in step 1
      FIX: result is clamped to [0.0, 1.0] before return
    """
    if action.action_type != "classify" or action.severity is None:
        return -0.1, {"reason": "wrong action type or missing severity"}

    correct   = code["ground_truth_severity"]
    predicted = action.severity.value
    c_idx     = SEVERITY_ORDER.index(correct)
    p_idx     = SEVERITY_ORDER.index(predicted)
    dist      = abs(c_idx - p_idx)

    score = max(0.1, 1.0 - dist * 0.3)

    # FIX: critical_module penalty — only apply when under-classifying, not over
    if code.get("critical_module") and p_idx < c_idx:
        score -= 0.2

    # Bonus: agent already ran detect in this episode correctly
    prior_actions = state.get("history", [])
    if any("detect" in h and "task_complete=True" in h for h in prior_actions):
        score = min(1.0, score + 0.1)

    # FIX: clamp — was missing, could return -0.1
    score = round(max(0.0, min(score, 1.0)), 2)

    return score, {
        "task_complete": dist == 0,
        "correct_severity": correct,
        "predicted": predicted,
        "distance": dist,
    }


# ── HARD: Full code review comment ─────────────────────────────────────────
def grade_full_review(action: Action, code: dict, state: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Rubric (max 1.0):
      - Preparation  (0.15): detect + classify done correctly before review
      - Word count   (0.10): ≥40 words
      - Issue mention(0.20): mentions each correct issue type
      - Severity     (0.10): mentions correct severity level
      - Keywords     (0.20): covers required technical keywords
      - Fix offered  (0.15): concrete fix suggestion language
      - Professional (0.10): polite, professional tone words
      - FP penalty  (-0.20): mentions issue on clean code
      - Anti-stuffing:       keyword-to-length ratio cap
    """
    if action.action_type != "review" or not action.comment:
        if action.action_type in ["detect", "classify"]:
            # Allow preparatory steps — count as partial effort
            return 0.05, {"reason": "preparatory step, not a review yet"}
        return 0.0, {"reason": "must use action_type=review with a comment"}

    comment       = action.comment.lower()
    score         = 0.0
    breakdown     = {}
    correct_issues = code["ground_truth_issues"]
    word_count    = len(comment.split())

    # ── Anti-keyword-stuffing guard ──────────────────────────────────────────
    # Count how many distinct issue-type words appear relative to comment length
    issue_word_hits = sum(1 for w in ALL_ISSUE_WORDS if w in comment)
    if word_count > 0 and (issue_word_hits / max(word_count, 1)) > 0.15:
        # >15% of words are issue-type labels → stuffing
        return 0.05, {"reason": "keyword stuffing detected — write a real review comment"}

    # ── 1. Preparation bonus (0.15) ──────────────────────────────────────────
    history = state.get("history", [])
    detected   = any("detect"   in h for h in history)
    classified = any("classify" in h for h in history)
    if detected and classified:
        score += 0.15; breakdown["preparation"] = 0.15
    elif detected or classified:
        score += 0.07; breakdown["preparation"] = 0.07

    # ── 2. Word count (0.10) ─────────────────────────────────────────────────
    if word_count >= 60:
        score += 0.10; breakdown["word_count"] = 0.10
    elif word_count >= 30:
        score += 0.05; breakdown["word_count"] = 0.05

    # ── 3. Issue mention (0.20) ──────────────────────────────────────────────
    if "none" not in correct_issues:
        matched_issues = [iss for iss in correct_issues if iss in comment]
        issue_ratio = len(matched_issues) / max(len(correct_issues), 1)
        issue_score = round(issue_ratio * 0.20, 3)
        score += issue_score
        breakdown["issue_mention"] = issue_score

    # ── 4. Severity (0.10) ───────────────────────────────────────────────────
    if code["ground_truth_severity"] in comment:
        score += 0.10; breakdown["severity"] = 0.10

    # ── 5. Technical keywords (0.20) ─────────────────────────────────────────
    keywords  = code.get("required_keywords", [])
    if keywords:
        kw_hits   = sum(1 for k in keywords if k.lower() in comment)
        kw_score  = round((kw_hits / len(keywords)) * 0.20, 3)
        score    += kw_score
        breakdown["keywords"] = kw_score

    # ── 6. Concrete fix suggestion (0.15) ────────────────────────────────────
    FIX_WORDS = ["use parameterized", "replace", "avoid", "refactor",
                 "use prepared", "sanitize", "validate", "add try", "handle"]
    if any(w in comment for w in FIX_WORDS):
        score += 0.15; breakdown["fix_suggestion"] = 0.15
    elif any(w in comment for w in ["fix", "change", "update"]):
        score += 0.07; breakdown["fix_suggestion"] = 0.07

    # ── 7. Professional tone (0.10) ──────────────────────────────────────────
    TONE_WORDS = ["recommend", "suggest", "consider", "would", "should"]
    if any(w in comment for w in TONE_WORDS):
        score += 0.10; breakdown["tone"] = 0.10

    # ── False positive penalty ───────────────────────────────────────────────
    if "none" in correct_issues and score > 0.05:
        score -= 0.20; breakdown["fp_penalty"] = -0.20

    score = round(max(0.0, min(score, 1.0)), 2)
    return score, {
        "task_complete": score >= 0.55,
        "score_breakdown": breakdown,
        "word_count": word_count,
    }
