# tasks/easy_task.py
TASK_CONFIG = {
    "name":        "issue_detection",
    "difficulty":  "easy",
    "description": (
        "Detect the type(s) of issue in the code diff. "
        "Types: bug, security, performance, style, none. "
        "Multi-issue detection supported via issue_types list. "
        "Graded by Jaccard similarity — partial credit for partial matches. "
        "False positives on clean code are penalized."
    ),
    "max_steps":          3,
    "success_threshold":  0.7,
    "required_action":    "detect",
    "scoring": {
        "exact_match":       0.92,
        "partial_credit":    "0.28 + 0.34*jaccard + 0.18*precision + 0.12*recall",
        "false_positive":    0.14,
        "false_negative":    0.12,
        "no_match":          0.16,
        "wrong_action":      0.18,
        "contract":          "all task scores remain strictly within (0, 1)",
    },
}
