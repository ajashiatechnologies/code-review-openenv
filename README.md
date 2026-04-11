---
title: Code Review OpenEnv
emoji: "🧠"
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🔍 Code Review OpenEnv

**A real-world AI agent evaluation environment for automated code review tasks.**

Built by **Ajashia Techno Wizards** for the Meta × Scaler OpenEnv Hackathon.

[![OpenEnv Validate](https://img.shields.io/badge/openenv%20validate-6%2F6%20passed-brightgreen)](https://huggingface.co/spaces/ajaykumar1523/code-review-openenv-ajashia-techno-wizards)
[![HF Space](https://img.shields.io/badge/HuggingFace-Space%20Live-blue)](https://huggingface.co/spaces/ajaykumar1523/code-review-openenv-ajashia-techno-wizards)

---

## Problem Statement

Every software company depends on code reviews to catch bugs, security vulnerabilities,
and performance problems before they reach production. But evaluating how well an AI
agent performs code review is hard — there is no standard benchmark, no graded
difficulty progression, and no structured reward signal.

This environment fills that gap. It models the real pull-request review workflow
and lets any LLM agent be benchmarked on a three-level task progression from
basic issue detection to full professional review generation.

---

## Environment Overview

An AI agent connects to this environment, receives a realistic code diff, and must:

1. **Detect** the type of issue present (bug, security, performance, style, or none)
2. **Classify** the severity considering module criticality and context
3. **Write** a professional code review comment with concrete fix suggestions

The environment grades every action with a structured reward signal and supports
multi-step episodes, session isolation, and multi-file context diffs.

---

## Observation Space

Each observation returned by `/reset` and `/step` contains:

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique episode identifier (UUID) |
| `diff` | string | The code diff to review |
| `language` | string | Programming language (python, java, javascript, go) |
| `file_name` | string | Source file name (e.g. `auth.py`, `UserService.java`) |
| `context` | string | Module context (e.g. `authentication module`) |
| `additional_files` | list[string] | Related context files for multi-file diffs |
| `history` | list[string] | Previous actions taken in this episode |
| `step_num` | int | Current step number (0-indexed) |
| `max_steps` | int | Maximum steps per episode (5) |

---

## Action Space

| Field | Type | Values |
|---|---|---|
| `action_type` | string | `detect` \| `classify` \| `review` |
| `issue_types` | list[string] | `bug` \| `security` \| `performance` \| `style` \| `none` |
| `severity` | string | `critical` \| `high` \| `medium` \| `low` |
| `line_numbers` | list[int] | Line numbers flagged (optional) |
| `comment` | string | Full review comment text (required for `review` action) |

---

## Tasks

### Easy — Issue Detection
Detect the type(s) of issue present in the code diff.

- **Required action:** `detect` with `issue_types`
- **Grading:** Jaccard similarity between predicted and correct issue sets
- **Scoring:** strict open-interval rewards only; exact matches score around `0.92`, partial matches stay in the mid-range, and wrong answers stay above `0.0`
- **Success threshold:** 0.70
- **Max steps:** 3

### Medium — Severity Classification
Classify the severity of the detected issue considering module criticality.

- **Required action:** `classify` with `severity`
- **Grading:** Distance on 4-level severity scale (critical > high > medium > low)
- **Scoring:** exact matches score around `0.90`, one-step misses around `0.72`, and under-classifying critical modules applies a small penalty while keeping scores strictly inside `(0, 1)`
- **Success threshold:** 0.80
- **Max steps:** 5

### Hard — Full Code Review
Multi-step pipeline: detect → classify → write a professional review comment.

- **Required actions:** `detect`, then `classify`, then `review`
- **Grading:** staged pipeline rewards for `detect` and `classify`, followed by a 7-criterion rubric for the final review comment
- **Success threshold:** 0.55
- **Max steps:** 5

#### Hard Task Rubric

| Criterion | Weight | Description |
|---|---|---|
| Base score | 0.18 | Gives the review stage a non-zero starting point while staying inside `(0, 1)` |
| Preparation bonus | 0.07 | Exact detect + classify completed before review |
| Word count | 0.10 | ≥ 60 words |
| Issue mention | 0.20 | Names every detected issue type |
| Severity mention | 0.10 | Uses the exact severity word |
| Technical keywords | 0.15 | Covers required domain terms (e.g. SQL injection, O(n²)) |
| Concrete fix | 0.10 | Uses replace/avoid/refactor/sanitize language |
| Professional tone | 0.08 | Uses recommend/suggest/consider |

Anti-gaming guard: keyword-stuffing detection caps the score at a low but still valid open-interval value.

---

## Example Scenario

```python
query = "SELECT * FROM users WHERE name = '" + name + "'"
for i in range(len(data)):
    for j in range(len(data)):
        process(data[i], data[j])
```

### Expected AI Behavior:

* Detect: SQL Injection (Security)
* Detect: Nested Loop (Performance)
* Assign Severity: Critical
* Suggest Fix: Use parameterized queries

---

## Evaluation Strategy

The environment ensures:

* Correct answers → High reward
* Partial answers → Moderate reward
* Incorrect answers → Low but still valid reward inside `(0, 1)`

---

## Baseline Agent

We provide a simple agent (`inference.py`) that:

* Interacts with the environment
* Produces baseline scores
* Demonstrates environment functionality

---

## How to Run

### 1. Start Environment

```bash
uvicorn env.environment:app --reload
```

### 2. Run Agent

```bash
python inference.py
```

---

## Docker Support

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

---

## API Endpoints

| Endpoint    | Description       |
| ----------- | ----------------- |
| POST /reset | Start new episode |
| POST /step  | Perform action    |
| GET /state  | Get current state |
| GET /health | Health check      |

---

## Why This Matters

This project demonstrates:

* AI evaluation system design
* Real-world problem modeling
* Reward engineering
* Multi-step reasoning environments

---

## Future Improvements

* Integrate real LLMs (GPT, LLaMA)
* Multi-file code context
* CI/CD pipeline integration
* Reinforcement learning training loop

---

## Team

**Ajashia Techno Wizards**

---

## Conclusion

This project moves beyond traditional ML by focusing on:

> “Building environments where intelligent agents can be evaluated, improved, and trusted in real-world scenarios.”

---
