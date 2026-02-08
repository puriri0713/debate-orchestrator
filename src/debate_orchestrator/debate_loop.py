from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import io
import re
from typing import Protocol, TextIO

from .agent_runner import AgentCallResult
from .config import DebateConfig
from .models import AgentRole, DebateState, ModeratorDecision, TurnMessage, TurnStatus
from .prompts import (
    build_debater_prompt,
    build_final_summary_prompt,
    build_moderator_decision_prompt,
    build_moderator_focus_prompt,
)

DECISION_RE = re.compile(r"DECISION:\s*(CONTINUE|STOP)", flags=re.IGNORECASE)
REASON_RE = re.compile(r"REASON:\s*(.+)", flags=re.IGNORECASE)
NEXT_FOCUS_RE = re.compile(r"NEXT_FOCUS:\s*(.+)", flags=re.IGNORECASE)
CONFIDENCE_RE = re.compile(r"CONFIDENCE:\s*([0-9]*\.?[0-9]+)", flags=re.IGNORECASE)
FOCUS_RE = re.compile(r"FOCUS:\s*(.+)", flags=re.IGNORECASE)

FALLBACK_DECISION_REASON = "司会判定ブロック欠落のため安全側で継続"


class RunnerProtocol(Protocol):
    def ask(self, prompt: str, timeout_sec: int, retry_count: int = 1) -> AgentCallResult:
        ...


@dataclass
class DebateResult:
    summary_markdown: str
    state: DebateState


def parse_focus(response: str, default_focus: str) -> str:
    focus_match = FOCUS_RE.search(response)
    if focus_match:
        return focus_match.group(1).strip()

    for line in response.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return default_focus


def _parse_confidence(raw_value: str) -> float:
    try:
        value = float(raw_value)
    except ValueError:
        return 0.5
    return max(0.0, min(1.0, value))


def parse_moderator_decision(response: str, fallback_focus: str) -> ModeratorDecision:
    decision_match = DECISION_RE.search(response)
    reason_match = REASON_RE.search(response)
    next_focus_match = NEXT_FOCUS_RE.search(response)
    confidence_match = CONFIDENCE_RE.search(response)

    if not all([decision_match, reason_match, next_focus_match, confidence_match]):
        return ModeratorDecision(
            continue_debate=True,
            reason=FALLBACK_DECISION_REASON,
            confidence=0.3,
            next_focus=fallback_focus,
        )

    decision_token = decision_match.group(1).upper()
    continue_debate = decision_token == "CONTINUE"
    reason = reason_match.group(1).strip()
    next_focus = next_focus_match.group(1).strip() or fallback_focus
    confidence = _parse_confidence(confidence_match.group(1))

    return ModeratorDecision(
        continue_debate=continue_debate,
        reason=reason,
        confidence=confidence,
        next_focus=next_focus,
    )


def should_stop(
    state: DebateState,
    config: DebateConfig,
    last_decision: ModeratorDecision | None,
    now: datetime | None = None,
) -> tuple[bool, str]:
    current_time = now or datetime.now(timezone.utc)

    if last_decision is not None and not last_decision.continue_debate:
        return True, last_decision.reason or "司会判定により終了"

    if state.round_index >= config.max_rounds:
        return True, f"最大ラウンド数({config.max_rounds})に到達"

    if state.deadline_at is not None and current_time >= state.deadline_at:
        return True, f"最大時間({config.max_minutes}分)に到達"

    return False, ""


def _render_live_line(stream: TextIO, line: str) -> None:
    stream.write(line + "\n")
    stream.flush()


def _append_turn(
    state: DebateState,
    role: AgentRole,
    round_index: int,
    prompt: str,
    result: AgentCallResult,
) -> TurnMessage:
    response = result.response.strip()
    if not response:
        if result.status == TurnStatus.TIMEOUT:
            response = "（タイムアウト）"
        elif result.status == TurnStatus.ERROR:
            response = f"（エラー: {result.error or 'unknown'}）"
        else:
            response = "（空応答）"

    turn = TurnMessage(
        role=role,
        round_index=round_index,
        prompt=prompt,
        response=response,
        elapsed_ms=result.elapsed_ms,
        status=result.status,
    )
    state.transcript.append(turn)
    return turn


def _format_live_snippet(text: str, width: int = 120) -> str:
    normalized = " ".join(text.split())
    if len(normalized) > width:
        return normalized[:width] + "..."
    return normalized


def _build_fallback_summary(state: DebateState) -> str:
    total_turns = len(state.transcript)
    return (
        "## 結論\n"
        f"- 司会要約の取得に失敗したため、フォールバックを返します。停止理由: {state.stop_reason}\n\n"
        "## 主な根拠\n"
        f"- 総ターン数: {total_turns}\n"
        f"- 実施ラウンド数: {state.round_index}\n\n"
        "## 反対意見・留保\n"
        "- 司会の最終要約が取得できていないため、論点の精査が必要です。\n\n"
        "## 未解決論点\n"
        "- 追加検証が必要な論点の再抽出。\n\n"
        "## 推奨アクション\n"
        "- 設定を調整して再実行し、司会要約の取得を確認する。\n"
    )


def _ensure_summary_sections(summary: str) -> str:
    required_sections = [
        "## 結論",
        "## 主な根拠",
        "## 反対意見・留保",
        "## 未解決論点",
        "## 推奨アクション",
    ]

    if not summary.strip():
        return ""

    output = summary.strip()
    for section in required_sections:
        if section not in output:
            output += f"\n\n{section}\n- （未記載）"
    return output + "\n"


def run_debate(
    config: DebateConfig,
    runner: RunnerProtocol,
    output_stream: TextIO | None = None,
) -> DebateResult:
    config.validate()

    started_at = datetime.now(timezone.utc)
    state = DebateState(
        topic=config.topic,
        round_index=0,
        transcript=[],
        started_at=started_at,
        deadline_at=started_at + timedelta(minutes=config.max_minutes),
    )

    live_stream: TextIO = output_stream if output_stream is not None else io.StringIO()
    current_focus = config.topic
    last_decision: ModeratorDecision | None = None

    while True:
        stop_now, reason = should_stop(state, config, last_decision)
        if stop_now:
            state.stop_reason = reason
            break

        state.round_index += 1
        round_index = state.round_index

        focus_prompt = build_moderator_focus_prompt(config.topic, round_index, state.transcript)
        focus_result = runner.ask(
            prompt=focus_prompt,
            timeout_sec=config.agent_timeout_sec,
            retry_count=config.retry_count,
        )
        focus_turn = _append_turn(
            state=state,
            role=AgentRole.MODERATOR,
            round_index=round_index,
            prompt=focus_prompt,
            result=focus_result,
        )
        current_focus = parse_focus(focus_turn.response, current_focus)

        if config.show_live:
            _render_live_line(
                live_stream,
                f"[round {round_index}] moderator focus: {_format_live_snippet(current_focus)}",
            )

        debater_turns: list[TurnMessage] = []
        for role in AgentRole.debaters(config.debater_count):
            debater_prompt = build_debater_prompt(
                role=role,
                topic=config.topic,
                round_index=round_index,
                focus=current_focus,
                transcript=state.transcript,
            )
            debater_result = runner.ask(
                prompt=debater_prompt,
                timeout_sec=config.agent_timeout_sec,
                retry_count=config.retry_count,
            )
            debater_turn = _append_turn(
                state=state,
                role=role,
                round_index=round_index,
                prompt=debater_prompt,
                result=debater_result,
            )
            debater_turns.append(debater_turn)

            if config.show_live:
                _render_live_line(
                    live_stream,
                    f"[round {round_index}] {role.value}: {_format_live_snippet(debater_turn.response)}",
                )

        decision_prompt = build_moderator_decision_prompt(
            topic=config.topic,
            round_index=round_index,
            focus=current_focus,
            debater_messages=debater_turns,
            transcript=state.transcript,
        )
        decision_result = runner.ask(
            prompt=decision_prompt,
            timeout_sec=config.agent_timeout_sec,
            retry_count=config.retry_count,
        )
        decision = parse_moderator_decision(
            response=decision_result.response,
            fallback_focus=current_focus,
        )

        if decision.reason == FALLBACK_DECISION_REASON:
            retry_prompt = decision_prompt + "\n\n必ず判定ブロック4行を正確に出力してください。"
            retry_result = runner.ask(
                prompt=retry_prompt,
                timeout_sec=config.agent_timeout_sec,
                retry_count=0,
            )
            retry_decision = parse_moderator_decision(
                response=retry_result.response,
                fallback_focus=current_focus,
            )
            if retry_decision.reason != FALLBACK_DECISION_REASON:
                decision_result = retry_result
                decision = retry_decision

        decision_text = (
            decision_result.response.strip()
            if decision_result.response.strip()
            else (
                f"DECISION: {'CONTINUE' if decision.continue_debate else 'STOP'}\n"
                f"REASON: {decision.reason}\n"
                f"NEXT_FOCUS: {decision.next_focus}\n"
                f"CONFIDENCE: {decision.confidence:.2f}"
            )
        )

        _append_turn(
            state=state,
            role=AgentRole.MODERATOR,
            round_index=round_index,
            prompt=decision_prompt,
            result=AgentCallResult(
                response=decision_text,
                status=decision_result.status,
                elapsed_ms=decision_result.elapsed_ms,
                error=decision_result.error,
                attempts=decision_result.attempts,
            ),
        )

        if config.show_live:
            label = "CONTINUE" if decision.continue_debate else "STOP"
            _render_live_line(
                live_stream,
                f"[round {round_index}] moderator decision: {label} ({decision.reason})",
            )

        current_focus = decision.next_focus or current_focus
        last_decision = decision

    final_prompt = build_final_summary_prompt(config.topic, state.transcript, state.stop_reason)
    final_result = runner.ask(
        prompt=final_prompt,
        timeout_sec=config.agent_timeout_sec,
        retry_count=config.retry_count,
    )
    summary = _ensure_summary_sections(final_result.response)
    if not summary:
        summary = _build_fallback_summary(state)

    if config.show_live:
        _render_live_line(live_stream, "[final] summary generated")

    return DebateResult(summary_markdown=summary, state=state)
