from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from debate_orchestrator.config import DebateConfig
from debate_orchestrator.debate_loop import should_stop
from debate_orchestrator.models import DebateState, ModeratorDecision


class TerminationTests(unittest.TestCase):
    def test_stop_when_moderator_requests_stop(self) -> None:
        config = DebateConfig(topic="x")
        now = datetime.now(timezone.utc)
        state = DebateState(topic="x", round_index=1, started_at=now, deadline_at=now + timedelta(minutes=10))
        decision = ModeratorDecision(False, "十分に収束", 0.8, "不要")

        stop, reason = should_stop(state, config, decision, now=now)

        self.assertTrue(stop)
        self.assertEqual(reason, "十分に収束")

    def test_stop_when_round_limit_reached(self) -> None:
        config = DebateConfig(topic="x", max_rounds=2)
        now = datetime.now(timezone.utc)
        state = DebateState(topic="x", round_index=2, started_at=now, deadline_at=now + timedelta(minutes=10))

        stop, reason = should_stop(state, config, None, now=now)

        self.assertTrue(stop)
        self.assertIn("最大ラウンド数", reason)

    def test_stop_when_time_limit_reached(self) -> None:
        config = DebateConfig(topic="x", max_minutes=1)
        now = datetime.now(timezone.utc)
        state = DebateState(topic="x", round_index=0, started_at=now - timedelta(minutes=2), deadline_at=now - timedelta(seconds=1))

        stop, reason = should_stop(state, config, None, now=now)

        self.assertTrue(stop)
        self.assertIn("最大時間", reason)


if __name__ == "__main__":
    unittest.main()
