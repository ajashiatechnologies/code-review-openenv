---
title: Code Review OpenEnv Ajashia Techno Wizards
emoji: 🤖
colorFrom: blue
colorTo: green
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
- **Scoring:** 1.0 exact match, 0.4–0.9 partial, -0.1 false negative, -0.2 false positive
- **Success threshold:** 0.70
- **Max steps:** 3

### Medium — Severity Classification
Classify the severity of the detected issue considering module criticality.

- **Required action:** `classify` with `severity`
- **Grading:** Distance on 4-level severity scale (critical > high > medium > low)
- **Scoring:** 1.0 exact, 0.7 one step off, 0.4 two steps off; -0.2 penalty for under-classifying critical modules
- **Success threshold:** 0.80
- **Max steps:** 5

### Hard — Full Code Review
Multi-step pipeline: detect → classify → write a professional review comment.

- **Required actions:** `detect`, then `classify`, then `review`
- **Grading:** 7-criterion rubric (see below)
- **Success threshold:** 0.55
- **Max steps:** 5

#### Hard Task Rubric

| Criterion | Weight | Description |
|---|---|---|
| Preparation bonus | 0.15 | Detect + classify completed before review |
| Word count | 0.10 | ≥ 60 words |
| Issue mention | 0.20 | Names every detected issue type |
| Severity mention | 0.10 | Uses the exact severity word |
| Technical keywords | 0.20 | Covers required domain terms (e.g. SQL injection, O(n²)) |
| Concrete fix | 0.15 | Uses replace/avoid/refactor/sanitize language |
| Professional tone | 0.10 | Uses recommend/suggest/consider |

Anti-gaming guard: keyword-stuffing detection (>15% issue-type density) caps the score at 0.05.

---

## Reward Design

| Situation | Reward |
|---|---|
| Exact correct answer | +1.0 |
| Partial Jaccard match | +0.4 to +0.9 |
| One severity level off | +0.7 |
| Two severity levels off | +0.4 |
| Preparatory step (detect/classify in hard task) | +0.05 |
| False positive (flagging clean code) | -0.2 |
| False negative (missing real issue) | -0.1 |
| Wrong action type | -0.1 |
| Under-classifying a critical module | -0.2 |

---

## Dataset

25 realistic code diff templates across:

- **Languages:** Python, Java, JavaScript, Go
- **Issue types:** SQL injection, XSS, hardcoded secrets, command injection, path traversal, NPE, off-by-one, resource leak, O(n²) loop, N+1 query, DOM thrashing, style issues, clean code
- **Contexts:** authentication, payment processing, API handler, service layer, frontend, configuration, file I/O
- **Difficulty pools:** easy draws single-issue non-critical diffs; medium draws high/critical severity; hard draws multi-issue or multi-file diffs

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Start new episode. Query param: `task=easy\|medium\|hard` |
| `/step` | POST | Submit action. Query params: `session_id` |
| `/state` | GET | Get current observation. Query params: `session_id` |
| `/health` | GET | Health check — returns `{"status": "healthy"}` |
| `/metadata` | GET | Environment name and description |
| `/schema` | GET | Action, observation, and state schemas |
| `/mcp` | POST | JSON-RPC endpoint for MCP compatibility |

---

## Baseline Scores

Scores from running `inference.py` with `meta-llama/Meta-Llama-3-8B-Instruct`:

| Task | Score | Threshold | Status |
|---|---|---|---|
| Easy — Issue Detection | 1.00 | 0.70 | ✅ PASS |
| Medium — Severity Classification | 1.00 | 0.80 | ✅ PASS |
| Hard — Full Code Review | 0.82 | 0.55 | ✅ PASS |

---

## Quick Start

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/code-review-env.git
cd code-review-env

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the environment server
uvicorn env.environment:app --host 0.0.0.0 --port 7860 --reload

# 5. Verify it's running
curl http://localhost:7860/health
```

### Run the Baseline Agent

```bash
# Set your HuggingFace token
export HF_TOKEN="hf_your_token_here"           # Mac/Linux
# $env:HF_TOKEN = "hf_your_token_here"         # Windows PowerShell

# Run inference against the local server
python inference.py
```

### Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Manual API Test

```bash
# Reset (start a new episode)
curl -X POST "http://localhost:7860/reset?task=easy"

# Take a step (use session_id from reset response)
curl -X POST "http://localhost:7860/step?session_id=YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "detect", "issue_types": ["security"]}'

# Get current state
curl "http://localhost:7860/state?session_id=YOUR_SESSION_ID"
```

---

## Deployment

Live on Hugging Face Spaces:
**https://huggingface.co/spaces/ajaykumar1523/code-review-openenv-ajashia-techno-wizards**

Set these Secrets in your Space (Settings → Variables and Secrets):

| Variable | Value |
|---|---|
| `API_BASE_URL` | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | `meta-llama/Meta-Llama-3-8B-Instruct` |
| `HF_TOKEN` | Your HuggingFace access token |
| `ENV_URL` | Your Space URL |

---

## Environment Design Decisions

**Session isolation:** Each `/reset` call creates a unique UUID session. Concurrent
evaluation requests cannot interfere with each other.

**Partial rewards throughout episodes:** Rather than binary end-of-episode rewards,
every step returns a meaningful signal. This enables RL agents to learn from
intermediate feedback.

**Context-aware severity:** The same bug in `auth.py` scores higher severity than
in `utils.py`. Module criticality is a first-class signal in the grader.

**Anti-gaming guards:** The hard task grader detects keyword stuffing (>15% issue-type
density) and caps the score at 0.05, preventing trivial reward hacking.

**Hallucination penalty:** Agents that flag issues in clean code receive -0.2 reward,
encouraging precision over recall.

---

## Project Structure

```
code-review-env/
├── inference.py          # Baseline LLM agent
├── openenv.yaml          # Environment metadata
├── Dockerfile
├── requirements.txt
├── env/
│   ├── environment.py    # FastAPI server (reset / step / state)
│   ├── models.py         # Pydantic schemas
│   ├── data_generator.py # 25 realistic code diff templates
│   └── graders.py        # Reward functions (easy / medium / hard)
├── tasks/
│   ├── easy_task.py
│   ├── medium_task.py
│   └── hard_task.py
└── tests/
    ├── test_graders.py   # 29 unit tests
    └── test_env.py       # 13 integration tests
```

---

## Team

**Ajashia Techno Wizards**
Built for the Meta × Scaler OpenEnv Hackathon — April 2026
