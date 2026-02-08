from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_AGENT_CMD = 'codex exec -c model_reasoning_effort="medium"'


@dataclass(frozen=True)
class DebateConfig:
    topic: str
    max_rounds: int = 6
    max_minutes: int = 20
    debater_count: int = 3
    agent_cmd: str = DEFAULT_AGENT_CMD
    show_live: bool = True
    output_file: Path | None = None
    agent_timeout_sec: int = 120
    retry_count: int = 1

    def validate(self) -> "DebateConfig":
        if not self.topic.strip():
            raise ValueError("--topic は必須です")
        if self.max_rounds < 1:
            raise ValueError("--max-rounds は1以上を指定してください")
        if self.max_minutes < 1:
            raise ValueError("--max-minutes は1以上を指定してください")
        if self.debater_count not in (2, 3):
            raise ValueError("--debater-count は2または3を指定してください")
        if self.agent_timeout_sec < 5:
            raise ValueError("--agent-timeout-sec は5以上を指定してください")
        if self.retry_count < 0:
            raise ValueError("--retry-count は0以上を指定してください")
        return self


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"真偽値として解釈できません: {value}")
