from __future__ import annotations

import unittest

from debate_orchestrator.debate_loop import FALLBACK_DECISION_REASON, parse_moderator_decision


class ParserTests(unittest.TestCase):
    def test_parse_valid_block(self) -> None:
        response = (
            "議論は概ね収束。\n"
            "DECISION: STOP\n"
            "REASON: 主論点の比較が完了\n"
            "NEXT_FOCUS: 不要\n"
            "CONFIDENCE: 0.90"
        )

        decision = parse_moderator_decision(response, fallback_focus="次論点")

        self.assertFalse(decision.continue_debate)
        self.assertEqual(decision.reason, "主論点の比較が完了")
        self.assertEqual(decision.next_focus, "不要")
        self.assertEqual(decision.confidence, 0.9)

    def test_parse_missing_block_returns_fallback(self) -> None:
        decision = parse_moderator_decision("判定ブロックなし", fallback_focus="保留論点")

        self.assertTrue(decision.continue_debate)
        self.assertEqual(decision.reason, FALLBACK_DECISION_REASON)
        self.assertEqual(decision.next_focus, "保留論点")
        self.assertEqual(decision.confidence, 0.3)

    def test_parse_confidence_is_clamped(self) -> None:
        response = (
            "DECISION: CONTINUE\n"
            "REASON: 継続\n"
            "NEXT_FOCUS: 追加検証\n"
            "CONFIDENCE: 1.8"
        )

        decision = parse_moderator_decision(response, fallback_focus="次")
        self.assertEqual(decision.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
