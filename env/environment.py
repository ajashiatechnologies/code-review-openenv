import uuid
import uvicorn
from typing import Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import Observation, Action, StepResult
from .data_generator import generate_code_diff
from .graders import grade_action

app = FastAPI(
    title="Code Review OpenEnv",
    description="AI agent environment for automated code review evaluation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SESSION STORAGE ─────────────────────────────────────
_sessions: Dict[str, dict] = {}


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


# ── POST /reset ─────────────────────────────────────────
@app.post("/reset", response_model=Observation)
async def reset(task: str = Query(default="easy")):

    if task not in {"easy", "medium", "hard"}:
        raise HTTPException(status_code=400, detail="Invalid task")

    session_id = str(uuid.uuid4())
    code = generate_code_diff(task)

    _sessions[session_id] = {
        "session_id": session_id,
        "code": code,
        "task": task,
        "step": 0,
        "max_steps": 5,
        "done": False,
        "total_reward": 0.0,
        "history": [],
    }

    return _build_observation(_sessions[session_id])


# ── POST /step ──────────────────────────────────────────
@app.post("/step", response_model=StepResult)
async def step(action: Action, session_id: str = Query(...)):

    session = _get_session(session_id)
    reward, info = grade_action(action, session)

    session["step"] += 1
    session["total_reward"] += reward

    session["history"].append(
        f"step={session['step']} | action={action.action_type} "
        f"| issue_types={action.issue_types} | severity={action.severity}"
    )

    done = (session["step"] >= session["max_steps"]) or info.get("task_complete", False)
    session["done"] = done

    if done:
        _sessions.pop(session_id, None)

    return StepResult(
        observation=_build_observation(session),
        reward=round(reward, 4),
        done=done,
        info={
            **info,
            "step": session["step"],
            "total_reward": round(session["total_reward"], 4),
            "episode_id": session["session_id"],
        }
    )


# ── GET /state ──────────────────────────────────────────
@app.get("/state", response_model=Observation)
async def state(session_id: str = Query(...)):
    session = _get_session(session_id)
    return _build_observation(session)


# ── FIXED: GET /health ─────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "healthy",  # 🔥 FIXED
        "environment": "code-review-openenv",
        "version": "1.0.0",
        "active_sessions": len(_sessions),
    }


# ── NEW: GET /metadata ─────────────────────────────────
@app.get("/metadata")
async def metadata():
    return {
        "name": "Code Review OpenEnv",
        "description": "AI agent environment for automated code review evaluation"
    }


# ── NEW: GET /schema ───────────────────────────────────
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
            "step": "int",
            "max_steps": "int",
            "history": "list"
        }
    }


# ── NEW: POST /mcp ─────────────────────────────────────
@app.post("/mcp")
async def mcp():
    return {
        "jsonrpc": "2.0",
        "result": "ok",
        "id": 1
    }


# ── RUN ───────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("env.environment:app", host="0.0.0.0", port=7860)