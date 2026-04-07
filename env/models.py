from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class IssueType(str, Enum):
    BUG         = "bug"
    SECURITY    = "security"
    PERFORMANCE = "performance"
    STYLE       = "style"
    NONE        = "none"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class Observation(BaseModel):
    session_id:       str                    # FIX: added for multi-session isolation
    diff:             str
    language:         str
    file_name:        str
    context:          str
    additional_files: List[str] = []
    history:          List[str] = []
    step_num:         int = 0
    max_steps:        int = 5


class Action(BaseModel):
    action_type:  str                        # detect | classify | review
    issue_types:  Optional[List[IssueType]] = None   # FIX: list, not single value
    severity:     Optional[Severity] = None
    line_numbers: Optional[List[int]] = None         # FIX: list for multi-issue
    comment:      Optional[str] = None


class StepResult(BaseModel):
    observation: Observation
    reward:      float
    done:        bool
    info:        Dict[str, Any] = {}


class ResetRequest(BaseModel):
    task: str = "easy"
