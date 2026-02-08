# debate-orchestrator

司会1名と議論者2〜3名の `codex` サブプロセスを使って、テーマ討論を自動進行し、最終的にMarkdown要約を出力するツールです。

## セットアップ

```bash
uv sync
```

## 実行例

```bash
uv run debate-orchestrator \
  --topic "社内ナレッジ共有を改善する方法" \
  --max-rounds 6 \
  --max-minutes 20 \
  --debater-count 3 \
  --agent-cmd 'codex exec -c model_reasoning_effort="medium"' \
  --show-live true
```

## 主なオプション

- `--topic` 必須
- `--max-rounds` デフォルト `6`
- `--max-minutes` デフォルト `20`
- `--debater-count` デフォルト `3`（`2` または `3`）
- `--agent-cmd` デフォルト `codex exec -c model_reasoning_effort="medium"`
- `--show-live` デフォルト `true`
- `--output-file` 指定時は指定先へ保存（未指定時は `./debate_summary/summary_YYYYMMDD_HHMMSS.md` に自動保存）

## 補足

- `--agent-cmd` には引数付きコマンドを指定できます（例: `"python tests/mock_agent.py"`）。
- 実行環境で `codex` コマンドが利用可能である前提です。
