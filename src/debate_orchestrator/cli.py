from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from .agent_runner import AgentRunner
from .config import DEFAULT_AGENT_CMD, DebateConfig, parse_bool
from .debate_loop import run_debate


def build_default_output_path(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / "debate_summary" / f"summary_{timestamp}.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="複数Codex自動討論オーケストレータ")
    parser.add_argument("--topic", required=True, help="討論テーマ")
    parser.add_argument("--max-rounds", type=int, default=6, help="最大ラウンド数")
    parser.add_argument("--max-minutes", type=int, default=20, help="最大実行分数")
    parser.add_argument("--debater-count", type=int, default=3, help="議論者数 (2 or 3)")
    parser.add_argument(
        "--agent-cmd",
        default=DEFAULT_AGENT_CMD,
        help="エージェント実行コマンド",
    )
    parser.add_argument("--show-live", type=parse_bool, default=True, help="逐次ログ表示")
    parser.add_argument("--output-file", type=Path, default=None, help="最終要約の保存先")
    parser.add_argument(
        "--agent-timeout-sec",
        type=int,
        default=120,
        help="各エージェント呼び出しのタイムアウト秒",
    )
    parser.add_argument(
        "--retry-count",
        type=int,
        default=1,
        help="失敗時のリトライ回数",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = DebateConfig(
            topic=args.topic,
            max_rounds=args.max_rounds,
            max_minutes=args.max_minutes,
            debater_count=args.debater_count,
            agent_cmd=args.agent_cmd,
            show_live=args.show_live,
            output_file=args.output_file,
            agent_timeout_sec=args.agent_timeout_sec,
            retry_count=args.retry_count,
        ).validate()
    except ValueError as error:
        parser.error(str(error))
        return 2

    runner = AgentRunner(config.agent_cmd)
    result = run_debate(
        config=config,
        runner=runner,
        output_stream=sys.stdout,
    )

    print("\n# 最終要約\n")
    print(result.summary_markdown)

    output_path = config.output_file or build_default_output_path(Path.cwd())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.summary_markdown, encoding="utf-8")
    print(f"保存先: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
