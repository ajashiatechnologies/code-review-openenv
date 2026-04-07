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
        "exact_match":       1.0,
        "partial_jaccard":   "0.4 + jaccard * 0.5",
        "false_positive":   -0.2,
        "false_negative":   -0.1,
        "keyword_stuffing":  0.1,
        "wrong_action":     -0.1,
    },
}
