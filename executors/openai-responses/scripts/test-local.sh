#!/usr/bin/env bash
# Local end-to-end test for the OpenAI Responses executor.
# Starts the executor, waits for it to be ready, sends test requests, then tears down.
#
# Usage:
#   OPENAI_API_KEY=sk-... ./scripts/test-local.sh
#   OPENAI_API_KEY=sk-... MODELS="gpt-4o-mini gpt-5" INPUT="Find McKinsey website" ./scripts/test-local.sh

set -euo pipefail

API_KEY="${OPENAI_API_KEY:?Set OPENAI_API_KEY}"
MODELS="${MODELS:-gpt-4o-mini gpt-4.1-nano gpt-5}"
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
INPUT="${INPUT:-Find the main website of Adam Grooming BN Ltd}"
TOOLS='[{"type":"web_search_preview","user_location":{"type":"approximate","country":"GB","city":"London","region":"London"}}]'

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Start executor ─────────────────────────────────────────────────────────────
echo "Starting executor (port: $PORT)..."
cd "$SCRIPT_DIR"
SESSIONS_DIR="$(mktemp -d)" uv run executor-openai-responses &
EXECUTOR_PID=$!
trap 'echo "Stopping executor..."; kill "$EXECUTOR_PID" 2>/dev/null; wait "$EXECUTOR_PID" 2>/dev/null || true' EXIT

# ── Wait for health ────────────────────────────────────────────────────────────
echo "Waiting for executor to be ready..."
for i in $(seq 1 20); do
  if curl -sf "http://$HOST:$PORT/health" > /dev/null 2>&1; then
    echo "Executor ready."
    break
  fi
  [ "$i" -eq 20 ] && { echo "ERROR: Executor did not become ready." >&2; exit 1; }
  sleep 0.5
done

# ── Run a test request for each model ─────────────────────────────────────────
run_test() {
  local model="$1"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Model : $model"
  echo "Input : $INPUT"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  PAYLOAD=$(cat <<EOF
{
  "agent": {
    "name": "website-search-agent",
    "namespace": "default",
    "prompt": "You are an expert web search agent. Find the main website of the given company. Return only the URL.",
    "model": {
      "name": "$model",
      "type": "openai",
      "config": {"openai": {"apiKey": "$API_KEY"}}
    },
    "annotations": {
      "executor-openai-responses.ark.mckinsey.com/tools": $(echo "$TOOLS" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip()))")
    }
  },
  "userInput": {"role": "user", "content": "$INPUT"},
  "conversationId": "test-$model-$$",
  "query_annotations": {},
  "execution_engine_annotations": {}
}
EOF
)

  RESPONSE=$(curl -sf -X POST "http://$HOST:$PORT/execute" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD") && echo "$RESPONSE" | python3 -m json.tool \
    || echo "ERROR: request failed for model $model" >&2
}

for model in $MODELS; do
  run_test "$model"
done
