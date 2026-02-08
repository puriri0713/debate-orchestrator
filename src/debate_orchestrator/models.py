from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    MODERATOR = "moderator"
    DEBATER_1 = "debater_1"
    DEBATER_2 = "debater_2"
    DEBATER_3 = "debater_3"

    @classmethod
    def debaters(cls, count: int) -> list["AgentRole"]:
        if count not in (2, 3):
            raise ValueError("debater count must be 2 or 3")
        roles = [cls.DEBATER_1, cls.DEBATER_2, cls.DEBATER_3]
        return roles[:count]


class TurnStatus(str, Enum):
    OK = "ok"
    TIMEOUT = "timeout"
    ERROR = "error"
    EMPTY = "empty"


@dataclass
class TurnMessage:
    role: AgentRole
    round_index: int
    prompt: str
    response: str
    elapsed_ms: int
    status: TurnStatus


@dataclass
class ModeratorDecision:
    continue_debate: bool
    reason: str
    confidence: float
    next_focus: str


@dataclass
class DebateState:
    topic: str
    round_index: int
    transcript: list[TurnMessage] = field(default_factory=list)
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    stop_reason: str = ""
