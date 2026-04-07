# 🚀 AI Code Review Evaluation Environment (OpenEnv)

## Overview

This project presents a **real-world AI evaluation environment** designed to assess the capabilities of intelligent agents in performing **automated code review tasks**.

Unlike traditional ML projects that focus on training models, this system focuses on **evaluating AI reasoning, decision-making, and structured problem-solving** using a reinforcement-learning-ready environment.

---

## Problem Statement

Modern software development relies heavily on **code reviews** to ensure:

* Code quality
* Security
* Performance optimization

However, evaluating AI systems for such tasks is challenging due to:

* Multi-step reasoning requirements
* Context-dependent decisions
* Lack of structured evaluation environments

---

## Our Solution

We built a **Code Review OpenEnv**, where AI agents:

1. Analyze real-world code diffs
2. Detect issues (bug, security, performance, style)
3. Classify severity
4. Generate professional review comments

---

## Key Features (Innovation Highlights)

### Multi-Issue Detection

* Supports **multiple issues in a single code snippet**
* Mimics real-world scenarios

### Context-Aware Severity Scoring

* Severity depends on module importance (e.g., authentication = critical)

### Hallucination Penalty

* Penalizes false positives when no issue exists
* Encourages reliable AI behavior

### Multi-Step Evaluation

* Easy → Issue detection
* Medium → Severity classification
* Hard → Full code review

### Structured Reward System

* Partial scoring (0.1–1.0)
* Realistic grading logic
* Encourages incremental improvement

---

## System Architecture

```
Agent (inference.py)
        ↓
Environment API (FastAPI)
        ↓
Data Generator → Code Diff
        ↓
Grader → Reward Calculation
        ↓
Next State → Agent
```

---

## Workflow

1. `/reset` → Generate code review task
2. Agent analyzes diff
3. `/step` → Submit action
4. Grader evaluates response
5. Reward returned

---

## Tasks

| Task                    | Description           | Difficulty |
| ----------------------- | --------------------- | ---------- |
| Issue Detection         | Identify issue type   | Easy       |
| Severity Classification | Assign severity level | Medium     |
| Full Code Review        | End-to-end review     | Hard       |

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
* Incorrect answers → Low/negative reward

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
