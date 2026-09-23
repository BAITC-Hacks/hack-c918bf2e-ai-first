#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="ai-first"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  exec tmux attach-session -t "$SESSION_NAME"
fi

tmux new-session -d -s "$SESSION_NAME" -n work -c "$PROJECT_DIR"
tmux split-window -h -t "$SESSION_NAME:work" -c "$PROJECT_DIR"
tmux split-window -v -t "$SESSION_NAME:work.0" -c "$PROJECT_DIR"
tmux split-window -v -t "$SESSION_NAME:work.2" -c "$PROJECT_DIR"
tmux select-layout -t "$SESSION_NAME:work" tiled

tmux select-pane -t "$SESSION_NAME:work.0" -T "CODEX backend + integration"
tmux select-pane -t "$SESSION_NAME:work.1" -T "CLAUDE frontend only"
tmux select-pane -t "$SESSION_NAME:work.2" -T "DOCKER logs + tests"
tmux select-pane -t "$SESSION_NAME:work.3" -T "REVIEW read-only"

tmux send-keys -t "$SESSION_NAME:work.0" "printf '\n[CODEX] backend/, Docker, integration, Git and README\nRun when ready: codex\n\n'" Enter
tmux send-keys -t "$SESSION_NAME:work.1" "printf '\n[CLAUDE] frontend/ only; Claude CLI is not currently in PATH\n\n'" Enter
tmux send-keys -t "$SESSION_NAME:work.2" "printf '\n[QA] docker compose, logs, curl and tests\n\n'" Enter
tmux send-keys -t "$SESSION_NAME:work.3" "printf '\n[REVIEW] read-only review; do not edit while implementation is active\n\n'" Enter

tmux select-pane -t "$SESSION_NAME:work.0"
exec tmux attach-session -t "$SESSION_NAME"
