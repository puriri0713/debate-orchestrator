from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest

from debate_orchestrator.agent_runner import AgentRunner
from debate_orchestrator.config import DebateConfig
from debate_orchestrator.debate_loop import run_debate


class DebateLoopIntegrationTests(unittest.TestCase):
    def test_run_debate_with_mock_agent(self) -> None:
        mock_agent = Path(__file__).with_name("mock_agent.py")
        command = f"{sys.executable} {mock_agent}"

        config = DebateConfig(
            topic="社内ドキュメント運用の改善策",
            max_rounds=3,
            max_minutes=10,
            debater_count=3,
            agent_cmd=command,
            show_live=True,
            agent_timeout_sec=10,
            retry_count=1,
        )

        stream = io.StringIO()
        result = run_debate(config=config, runner=AgentRunner(command), output_stream=stream)

        self.assertGreaterEqual(result.state.round_index, 1)
        self.assertIn("## 結論", result.summary_markdown)
        self.assertIn("## 主な根拠", result.summary_markdown)
        self.assertIn("## 反対意見・留保", result.summary_markdown)
        self.assertIn("## 未解決論点", result.summary_markdown)
        self.assertIn("## 推奨アクション", result.summary_markdown)
        self.assertIn("[round 1]", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
