from __future__ import annotations

import re
import sys


def _extract_round(prompt: str) -> int:
    match = re.search(r"ラウンド番号:\s*(\d+)", prompt)
    if not match:
        return 1
    return int(match.group(1))


def main() -> int:
    prompt = sys.stdin.read()
    round_index = _extract_round(prompt)

    if "最終報告" in prompt or "最終要約" in prompt:
        print(
            "## 結論\n"
            "- 施策は段階導入が妥当。\n\n"
            "## 主な根拠\n"
            "- 実現性・リスク・運用コストの観点で共通して段階導入が優位。\n\n"
            "## 反対意見・留保\n"
            "- 初期段階での成果指標設計が不十分な可能性。\n\n"
            "## 未解決論点\n"
            "- 成果指標の閾値設定。\n\n"
            "## 推奨アクション\n"
            "- 2週間の試行期間を設定して再評価する。"
        )
        return 0

    if "最後に必ず次の判定ブロックを含めてください" in prompt:
        if round_index >= 2:
            print(
                "DECISION: STOP\n"
                "REASON: 主要論点の比較が完了したため\n"
                "NEXT_FOCUS: 不要\n"
                "CONFIDENCE: 0.84"
            )
        else:
            print(
                "DECISION: CONTINUE\n"
                "REASON: 追加比較が必要\n"
                "NEXT_FOCUS: リスク許容度と運用体制の整合\n"
                "CONFIDENCE: 0.71"
            )
        return 0

    role_match = re.search(r"あなたの役割ID:\s*(debater_[1-3])", prompt)
    role = role_match.group(1) if role_match else "debater_1"

    if role_match:
        print(
            "- 主張: 段階導入で失敗コストを下げるべき。\n"
            f"- 根拠: {role} の観点から、先行指標を定義して進めると意思決定しやすい。\n"
            "- 反証可能性: 先行導入で効果が出なければ全体展開は見送る。\n"
            "- 追加検証案: 2週間の試行で指標推移を測定する。"
        )
        return 0

    if "FOCUS:" in prompt:
        print("今回の論点は導入順序とガードレール設計です。\nFOCUS: 導入順序とガードレール")
        return 0

    print("FOCUS: 導入順序とガードレール")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
