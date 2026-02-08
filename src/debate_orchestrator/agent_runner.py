from __future__ import annotations

from dataclasses import dataclass
import shlex
import subprocess
import time

from .models import TurnStatus


@dataclass
class AgentCallResult:
    response: str
    status: TurnStatus
    elapsed_ms: int
    error: str | None = None
    attempts: int = 1


class AgentRunner:
    def __init__(self, agent_cmd: str) -> None:
        command = shlex.split(agent_cmd)
        if not command:
            raise ValueError("agent_cmd が空です")
        self._command = command

    def ask(self, prompt: str, timeout_sec: int, retry_count: int = 1) -> AgentCallResult:
        attempts = retry_count + 1
        last_result: AgentCallResult | None = None

        for attempt in range(1, attempts + 1):
            start = time.monotonic()
            try:
                completed = subprocess.run(
                    self._command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_sec,
                    check=False,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)
                stdout = completed.stdout.strip()
                stderr = completed.stderr.strip()

                if completed.returncode != 0:
                    last_result = AgentCallResult(
                        response=stdout,
                        status=TurnStatus.ERROR,
                        elapsed_ms=elapsed_ms,
                        error=stderr or f"終了コード: {completed.returncode}",
                        attempts=attempt,
                    )
                elif not stdout:
                    last_result = AgentCallResult(
                        response="",
                        status=TurnStatus.EMPTY,
                        elapsed_ms=elapsed_ms,
                        error="空の応答です",
                        attempts=attempt,
                    )
                else:
                    return AgentCallResult(
                        response=stdout,
                        status=TurnStatus.OK,
                        elapsed_ms=elapsed_ms,
                        attempts=attempt,
                    )
            except subprocess.TimeoutExpired:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                last_result = AgentCallResult(
                    response="",
                    status=TurnStatus.TIMEOUT,
                    elapsed_ms=elapsed_ms,
                    error=f"タイムアウト: {timeout_sec}秒",
                    attempts=attempt,
                )
            except OSError as error:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                last_result = AgentCallResult(
                    response="",
                    status=TurnStatus.ERROR,
                    elapsed_ms=elapsed_ms,
                    error=f"起動失敗: {error}",
                    attempts=attempt,
                )

        if last_result is None:
            raise RuntimeError("AgentRunner.ask が結果を返せませんでした")
        return last_result
