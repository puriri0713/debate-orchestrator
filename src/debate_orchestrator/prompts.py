from __future__ import annotations

from .models import AgentRole, TurnMessage


PERSPECTIVE_MAP = {
    AgentRole.DEBATER_1: "実現性（技術・体制・実行順序）",
    AgentRole.DEBATER_2: "リスク（失敗要因・副作用・回避策）",
    AgentRole.DEBATER_3: "コスト/運用（費用対効果・運用負荷・継続性）",
}


def _format_recent_transcript(transcript: list[TurnMessage], limit: int = 8) -> str:
    if not transcript:
        return "（まだ履歴はありません）"

    lines: list[str] = []
    for turn in transcript[-limit:]:
        snippet = turn.response.replace("\n", " ").strip()
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        lines.append(
            f"- round={turn.round_index} role={turn.role.value} status={turn.status.value}: {snippet}"
        )
    return "\n".join(lines)


def build_moderator_focus_prompt(topic: str, round_index: int, transcript: list[TurnMessage]) -> str:
    history = _format_recent_transcript(transcript)
    return f"""
あなたは討論の司会役です。
目的は、議論を収束させるために今回ラウンドで最も重要な論点を1つに絞ることです。

テーマ: {topic}
ラウンド番号: {round_index}
直近履歴:
{history}

出力ルール:
1) 1〜2文で論点を説明
2) 最後に必ず次の形式を含める
FOCUS: <今回の論点>
""".strip()


def build_debater_prompt(
    role: AgentRole,
    topic: str,
    round_index: int,
    focus: str,
    transcript: list[TurnMessage],
) -> str:
    perspective = PERSPECTIVE_MAP.get(role, "一般観点")
    history = _format_recent_transcript(transcript)
    return f"""
あなたは討論参加者です。

テーマ: {topic}
ラウンド番号: {round_index}
あなたの役割ID: {role.value}
あなたの観点: {perspective}
今回の論点: {focus}
直近履歴:
{history}

出力形式:
- 主張:
- 根拠:
- 反証可能性:
- 追加検証案:

上記4項目を必ず埋めてください。
""".strip()


def build_moderator_decision_prompt(
    topic: str,
    round_index: int,
    focus: str,
    debater_messages: list[TurnMessage],
    transcript: list[TurnMessage],
) -> str:
    history = _format_recent_transcript(transcript)
    debater_blocks = []
    for message in debater_messages:
        debater_blocks.append(f"[{message.role.value}]\n{message.response}")
    debaters_text = "\n\n".join(debater_blocks)

    return f"""
あなたは討論の司会役です。
議論を収束させる責任があります。感想ではなく意思決定に必要な比較を優先してください。

テーマ: {topic}
ラウンド番号: {round_index}
今回の論点: {focus}
議論者の回答:
{debaters_text}

直近履歴:
{history}

最後に必ず次の判定ブロックを含めてください:
DECISION: CONTINUE または STOP
REASON: <判断理由>
NEXT_FOCUS: <次ラウンドで扱う論点>
CONFIDENCE: <0.0〜1.0>
""".strip()


def build_final_summary_prompt(topic: str, transcript: list[TurnMessage], stop_reason: str) -> str:
    history = _format_recent_transcript(transcript, limit=20)
    return f"""
あなたは討論の司会役です。討論結果を最終報告としてまとめてください。

テーマ: {topic}
停止理由: {stop_reason}
討論履歴:
{history}

次の見出しをこの順で必ず出力してください:
## 結論
## 主な根拠
## 反対意見・留保
## 未解決論点
## 推奨アクション
""".strip()
