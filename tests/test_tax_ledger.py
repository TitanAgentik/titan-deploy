"""Unit tests for tax ledger stub."""

from __future__ import annotations

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "templates" / "capital"))
from tax_ledger import TaxLedger  # noqa: E402


def test_acquisition_and_fifo_disposal(tmp_path: Path) -> None:
    ledger = TaxLedger(tmp_path / "tax.jsonl")
    lot = ledger.record_acquisition("USDC", 1000.0, 1000.0, source="deposit")
    assert lot.lot_id.startswith("lot-")
    disposals = ledger.record_disposal_fifo("USDC", 500.0, 500.0)
    assert len(disposals) == 1
    assert disposals[0].gain_loss_usd == 0.0


def test_export_csv(tmp_path: Path) -> None:
    ledger = TaxLedger(tmp_path / "tax.jsonl")
    ledger.record_acquisition("ETH", 1.0, 3000.0)
    csv_out = ledger.export_csv()
    assert "lot_id" in csv_out
    assert "ETH" in csv_out


def test_capital_event_sync(tmp_path: Path) -> None:
    ledger = TaxLedger(tmp_path / "tax.jsonl")
    result = ledger.sync_from_capital_event(
        {"action": "deposit", "asset": "USDC", "amount": 100, "amount_usd": 100}
    )
    assert result["synced"] is True
