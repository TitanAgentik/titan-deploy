#!/usr/bin/env bash
# Local DeepSeek-V4-Flash (Tier 3a style) on TITANSPARK — :30005 offline R&D only.
# Never route TRENCH-OPS / GUARDIAN / EXECUTOR here.
set -euo pipefail

ROOT="${TITAN_LAUNCH_ROOT:-$HOME/Documents/Cursor Projects/titan-launch}"
BIN="${ROOT}/local-ai/bin/vulkan"
MODEL="${TITAN_DEEPSEEK_MODEL:-${ROOT}/local-ai/models/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-MXFP4/DeepSeek-V4-Flash-MXFP4-00001-of-00004.gguf}"
HOST="${TITAN_INFER_HOST:-0.0.0.0}"
PORT="${TITAN_INFER_PORT:-30005}"
CTX="${TITAN_CTX:-8192}"

if [[ ! -f "$MODEL" ]]; then
  echo "ERROR: model not found: $MODEL" >&2
  echo "Download: hf download bartowski/DeepSeek-V4-Flash-GGUF --include 'DeepSeek-V4-Flash-MXFP4*' --local-dir ${ROOT}/local-ai/models/DeepSeek-V4-Flash-GGUF" >&2
  exit 1
fi
if [[ ! -x "$BIN/llama-server" ]]; then
  echo "ERROR: missing $BIN/llama-server" >&2
  exit 1
fi

export LD_LIBRARY_PATH="${BIN}:${LD_LIBRARY_PATH:-}"
exec "$BIN/llama-server" \
  --host "$HOST" --port "$PORT" \
  --model "$MODEL" \
  --alias deepseek-ai/DeepSeek-V4-Flash \
  --ctx-size "$CTX" \
  --parallel 1 \
  --n-gpu-layers "${TITAN_NGL:-999}" \
  --cpu-moe \
  --flash-attn on \
  --jinja \
  --threads "${TITAN_THREADS:-16}"
