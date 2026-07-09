#!/usr/bin/env python3
"""Normalize TITAN.md: unescape markdown and fix known broken content."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NORMALIZED_PATH, OUTPUT_DIR, read_source, unescape_markdown, write_text


def fix_broken_rows(text: str) -> str:
    """Fix truncated circuit-breaker / table rows."""
    text = text.replace(
        "CB: ` bridge rebalance), `CB_P17_BRIDGE_DELAY`",
        "CB: `CB_P17_INVENTORY_LOW` (pre-positioned inventory < minimum → flash-loan on-demand inventory via §FL), "
        "`CB_P17_BRIDGE_DELAY`",
    )
    return text


def normalize_code_fences(text: str) -> str:
    """Clean up malformed fence markers around deploy blocks."""
    text = re.sub(r"```text\s*\nDeploy to:", "Deploy to:", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize TITAN.md")
    parser.add_argument("source", type=Path, help="Path to TITAN.md")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=NORMALIZED_PATH,
        help="Output path",
    )
    args = parser.parse_args()

    raw = read_source(args.source)
    text = unescape_markdown(raw)
    text = fix_broken_rows(text)
    text = normalize_code_fences(text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_text(args.output, text)
    print(f"Normalized {len(raw)} -> {len(text)} chars -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
