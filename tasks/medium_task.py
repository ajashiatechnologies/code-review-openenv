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
        "exact_match":              1.0,
        "one_step_off":             0.7,
        "two_steps_off":            0.4,
        "three_steps_off":          0.1,
        "critical_module_underclassify_penalty": -0.2,
        "prior_detection_bonus":    0.1,
        "wrong_action":            -0.1,
        "clamp":                   "[0.0, 1.0]",
    },
}
