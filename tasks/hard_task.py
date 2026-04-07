# tasks/hard_task.py
TASK_CONFIG = {
    "name":        "full_code_review",
    "difficulty":  "hard",
    "description": (
        "Multi-step pipeline: (1) detect issues, (2) classify severity, "
        "(3) write a professional review comment. "
        "Comment graded on 7-criterion rubric: preparation, word count, "
        "issue mention, severity, keyword coverage, fix suggestion, tone. "
        "Anti-keyword-stuffing guard prevents trivial gaming. "
        "Designed to require reasoning that challenges frontier LLMs."
    ),
    "max_steps":          5,
    "success_threshold":  0.55,
    "required_action_final": "review",
    "rubric": {
        "preparation_bonus":    0.15,
        "word_count":           0.10,
        "issue_mention":        0.20,
        "severity_mention":     0.10,
        "keyword_coverage":     0.20,
        "fix_suggestion":       0.15,
        "professional_tone":    0.10,
    },
    "penalties": {
        "false_positive":      -0.20,
        "keyword_stuffing":     0.05,
    },
}
