#!/usr/bin/env bash
# Warm Tier 1 KV cache for GUARDIAN + TRENCH-OPS system prompts (~200ms vs ~2s cold)
set -euo pipefail
sleep 2
curl -sf -m 30 http://127.0.0.1:30000/health >/dev/null || exit 0
curl -sf -m 60 http://127.0.0.1:30000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"warm","messages":[{"role":"system","content":"TITAN prewarm GUARDIAN TRENCH-OPS gate path"}],"max_tokens":1,"temperature":0}' \
  >/dev/null || true
