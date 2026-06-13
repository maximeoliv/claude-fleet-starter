"""Models for the local state agent."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ActionType = Literal[
    "Bash", "Read", "Edit", "Write", "WebFetch", "WebSearch",
    "MCP", "Agent", "NotebookEdit", "Unknown",
]
DangerLevel = Literal["green", "yellow", "orange", "red"]
StressLevel = Literal["green", "yellow", "orange", "red", "unknown"]


class PromptInfo(BaseModel):
    active: bool
    type: ActionType = "Unknown"
    subject: Optional[str] = None
    danger: DangerLevel = "orange"
    options: list[str] = []


class PressureInfo(BaseModel):
    io_some_avg10: float = 0.0
    io_full_avg10: float = 0.0
    cpu_some_avg10: float = 0.0
    mem_some_avg10: float = 0.0
    mem_full_avg10: float = 0.0
    load_1min: float = 0.0
    stress_level: StressLevel = "unknown"


class TransferSummary(BaseModel):
    id: str
    sender: Optional[str] = None
    subject: Optional[str] = None
    priority: Optional[str] = None
    attachments: list[str] = []


class LocalState(BaseModel):
    """Full state of this machine, generated locally (no SSH)."""
    host: str
    claude_running: bool = False
    tmux_session: bool = False
    remote_control: bool = False
    state_label: str = "unknown"
    session_url: Optional[str] = None
    prompt: PromptInfo = PromptInfo(active=False)
    pressure: PressureInfo = PressureInfo()
    transfers_unread: int = 0
    transfers: list[TransferSummary] = []
    generated_at: float = 0.0


class SessionInfo(BaseModel):
    """State of a single tmux session (may or may not have claude running)."""
    name: str
    claude_running: bool = False
    remote_control: bool = False
    state_label: str = "unknown"


class ActionRequest(BaseModel):
    action: Literal[
        "accept_once", "accept_all", "reject", "esc",
        "compact_confirm", "clear_confirm",
    ]


class InjectRequest(BaseModel):
    message: str
