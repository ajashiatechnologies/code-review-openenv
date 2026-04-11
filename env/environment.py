import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware

from .models import Observation, Action, StepResult, IssueType, Severity
from .data_generator import generate_code_diff
from .graders import grade_action, normalize_score

app = FastAPI(
    title="Code Review OpenEnv",
    description="AI agent environment for automated code review evaluation",
    version="1.0.0"
)

# Compatibility alias for ASGI loaders that look for `application`.
application = app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SESSION STORAGE ─────────────────────────────────────
_sessions: Dict[str, dict] = {}
TASK_MAX_STEPS = {
    "easy": 3,
    "medium": 5,
    "hard": 5,
}


def _get_session(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if not session or session.get("done"):
        raise HTTPException(
            status_code=400,
            detail=f"No active episode for session '{session_id}'. Call POST /reset first."
        )
    return session


def _build_observation(session: dict) -> Observation:
    code = session["code"]
    return Observation(
        session_id=session["session_id"],
        diff=code["diff"],
        language=code["language"],
        file_name=code["file_name"],
        context=code["context"],
        additional_files=code.get("additional_files", []),
        history=session.get("history", []),
        step_num=session["step"],
        max_steps=session["max_steps"],
    )

def _coerce_action(payload: Any) -> Action:
    """Best-effort parse to avoid 422s from imperfect agent outputs."""
    if not isinstance(payload, dict):
        payload = {}

    action_type = str(payload.get("action_type", "review")).lower().strip()
    if action_type not in {"detect", "classify", "review"}:
        action_type = "review"

    issue_types: List[IssueType] = []
    raw_issues = payload.get("issue_types")
    if isinstance(raw_issues, list):
        for item in raw_issues:
            value = str(item).lower().strip()
            if value in IssueType._value2member_map_:
                issue_types.append(IssueType(value))

    severity = None
    raw_severity = payload.get("severity")
    if raw_severity is not None:
        value = str(raw_severity).lower().strip()
        if value in Severity._value2member_map_:
            severity = Severity(value)

    line_numbers = None
    raw_lines = payload.get("line_numbers")
    if isinstance(raw_lines, list):
        parsed_lines = []
        for item in raw_lines:
            try:
                parsed_lines.append(int(item))
            except (TypeError, ValueError):
                continue
        line_numbers = parsed_lines or None

    comment = payload.get("comment")
    if comment is not None:
        comment = str(comment)

    return Action(
        action_type=action_type,
        issue_types=issue_types or None,
        severity=severity,
        line_numbers=line_numbers,
        comment=comment,
    )


# ── POST /reset ─────────────────────────────────────────
@app.post("/reset", response_model=Observation)
async def reset(task: str = Query(default="easy")):
    task_aliases = {
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
        "issue_detection": "easy",
        "severity_classification": "medium",
        "full_code_review": "hard",
    }
    normalized_task = task_aliases.get(task)
    if normalized_task is None:
        raise HTTPException(status_code=400, detail="Invalid task")

    session_id = str(uuid.uuid4())
    code = generate_code_diff(normalized_task)

    _sessions[session_id] = {
        "session_id": session_id,
        "code": code,
        "task": normalized_task,
        "step": 0,
        "max_steps": TASK_MAX_STEPS[normalized_task],
        "done": False,
        "history": [],
        "total_reward": 0.0,
    }

    return _build_observation(_sessions[session_id])


# ── POST /step ──────────────────────────────────────────
@app.post("/step", response_model=StepResult)
async def step(action: Any = Body(...), session_id: str = Query(...)):

    session = _get_session(session_id)
    safe_action = _coerce_action(action)

    try:
        reward, info = grade_action(safe_action, session)
    except Exception as exc:
        reward, info = 0.5, {"reason": f"step_exception:{type(exc).__name__}"}

    # Double safety clamping
    reward = normalize_score(reward)

    session["step"] += 1

    if "total_reward" not in session:
        session["total_reward"] = 0.0

    session["total_reward"] += reward
    session["total_reward"] = normalize_score(session["total_reward"])

    session["history"].append(
        f"step={session['step']} | action={safe_action.action_type} "
        f"| issue_types={safe_action.issue_types} | severity={safe_action.severity} "
        f"| task_complete={info.get('task_complete', False)} "
        f"| reason={info.get('reason', '')}"
    )

    done = (session["step"] >= session["max_steps"]) or bool(info.get("task_complete", False))
    session["done"] = done

    if done:
        _sessions.pop(session_id, None)

    return StepResult(
        observation=_build_observation(session),
        reward=reward,
        done=done,
        info={
            **info,
            "step": session["step"],
            "total_reward": session["total_reward"],
            "episode_id": session["session_id"],
        }
    )


# ── GET /state ──────────────────────────────────────────
@app.get("/state", response_model=Observation)
async def state(session_id: str = Query(...)):
    session = _get_session(session_id)
    return _build_observation(session)


# ── GET /health ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "environment": "code-review-openenv",
        "version": "1.0.0",
        "active_sessions": len(_sessions),
    }


# ── GET /metadata ───────────────────────────────────────
@app.get("/metadata")
async def metadata():
    return {
        "name": "Code Review OpenEnv",
        "description": "AI agent environment for automated code review evaluation"
    }


# ── GET /schema ─────────────────────────────────────────
@app.get("/schema")
async def schema():
    return {
        "action": {
            "action_type": "detect | classify | review",
            "issue_types": ["bug", "security", "performance", "style", "none"],
            "severity": ["critical", "high", "medium", "low"],
            "comment": "string"
        },
        "observation": {
            "diff": "string",
            "language": "string",
            "file_name": "string",
            "context": "string"
        },
        "state": {
            "session_id": "string",
            "task": "easy | medium | hard",
            "step": "integer",
            "max_steps": "integer",
            "history": ["string"],
            "total_reward": "float"
        }
    }


# ── POST /mcp ───────────────────────────────────────────
@app.post("/mcp")
async def mcp():
    return {
        "jsonrpc": "2.0",
        "result": "ok",
        "id": 1
    }
