# tasks/medium_task.py
TASK_CONFIG = {
    "name":        "severity_classification",
    "difficulty":  "medium",
    "description": (
        "Classify the severity of the detected issue: critical, high, medium, low. "
        "Context-aware: critical modules (auth, payment) demand higher severity. "
        "Prior correct detection earns a +0.1 bonus. "
        "Graded by distance on 4-level severity scale."
    ),
    "max_steps":          5,
    "success_threshold":  0.8,
    "required_action":    "classify",
    "scoring": {
        "exact_match":              0.90,
        "one_step_off":             0.72,
        "two_steps_off":            0.46,
        "three_steps_off":          0.20,
        "critical_module_underclassify_penalty": 0.08,
        "prior_detection_bonus":    0.04,
        "detect_prep_step":         "0.18 + (detect_score - 0.02) * 0.45",
        "wrong_action":             0.18,
        "contract":                 "all task scores remain strictly within (0, 1)",
    },
}
