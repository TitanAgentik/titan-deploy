"""Tax/compliance ledger stub — cost-basis per lot, CSV export."""

from __future__ import annotations

import csv
import io
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_TAX_PATH = Path.home() / ".openclaw" / "capital" / "tax_lots.jsonl"


@dataclass
class TaxLot:
    lot_id: str
    asset: str
    quantity: float
    cost_basis_usd: float
    acquired_at: float
    source: str = "deposit"
    disposed: bool = False
    disposed_at: float | None = None
    proceeds_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DisposalRecord:
    disposal_id: str
    lot_id: str
    asset: str
    quantity: float
    proceeds_usd: float
    cost_basis_usd: float
    gain_loss_usd: float
    disposed_at: float
    tx_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaxLedger:
    """FIFO cost-basis tracking stub wired to capital audit events."""

    def __init__(self, ledger_path: Path | None = None) -> None:
        self.ledger_path = ledger_path or DEFAULT_TAX_PATH
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._lots: list[TaxLot] = self._load()

    def _load(self) -> list[TaxLot]:
        if not self.ledger_path.exists():
            return []
        lots = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("type") == "lot":
                lots.append(TaxLot(**{k: v for k, v in record.items() if k != "type"}))
        return lots

    def _append(self, record: dict[str, Any]) -> None:
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def record_acquisition(
        self,
        asset: str,
        quantity: float,
        cost_basis_usd: float,
        source: str = "deposit",
        tx_ref: str = "",
    ) -> TaxLot:
        lot = TaxLot(
            lot_id=f"lot-{uuid.uuid4().hex[:8]}",
            asset=asset,
            quantity=quantity,
            cost_basis_usd=cost_basis_usd,
            acquired_at=time.time(),
            source=source,
        )
        self._lots.append(lot)
        self._append({"type": "lot", **lot.to_dict(), "tx_ref": tx_ref})
        return lot

    def record_disposal_fifo(
        self, asset: str, quantity: float, proceeds_usd: float, tx_ref: str = ""
    ) -> list[DisposalRecord]:
        remaining = quantity
        disposals: list[DisposalRecord] = []
        for lot in self._lots:
            if remaining <= 0:
                break
            if lot.asset != asset or lot.disposed:
                continue
            take = min(remaining, lot.quantity)
            cost_portion = (take / lot.quantity) * lot.cost_basis_usd if lot.quantity else 0
            gain = proceeds_usd * (take / quantity) - cost_portion if quantity else 0
            disp = DisposalRecord(
                disposal_id=f"disp-{uuid.uuid4().hex[:8]}",
                lot_id=lot.lot_id,
                asset=asset,
                quantity=take,
                proceeds_usd=proceeds_usd * (take / quantity) if quantity else 0,
                cost_basis_usd=cost_portion,
                gain_loss_usd=gain,
                disposed_at=time.time(),
                tx_ref=tx_ref,
            )
            disposals.append(disp)
            self._append({"type": "disposal", **disp.to_dict()})
            lot.quantity -= take
            if lot.quantity <= 0:
                lot.disposed = True
                lot.disposed_at = time.time()
                lot.proceeds_usd = disp.proceeds_usd
            remaining -= take
        return disposals

    def open_lots(self, asset: str | None = None) -> list[dict[str, Any]]:
        lots = [l for l in self._lots if not l.disposed]
        if asset:
            lots = [l for l in lots if l.asset == asset]
        return [l.to_dict() for l in lots]

    def export_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "lot_id",
                "asset",
                "quantity",
                "cost_basis_usd",
                "acquired_at",
                "source",
                "disposed",
                "proceeds_usd",
                "gain_loss_usd",
            ]
        )
        for lot in self._lots:
            writer.writerow(
                [
                    lot.lot_id,
                    lot.asset,
                    lot.quantity,
                    lot.cost_basis_usd,
                    lot.acquired_at,
                    lot.source,
                    lot.disposed,
                    lot.proceeds_usd or "",
                    "",
                ]
            )
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines() if self.ledger_path.exists() else []:
            rec = json.loads(line)
            if rec.get("type") == "disposal":
                writer.writerow(
                    [
                        rec.get("lot_id"),
                        rec.get("asset"),
                        rec.get("quantity"),
                        rec.get("cost_basis_usd"),
                        rec.get("disposed_at"),
                        "disposal",
                        True,
                        rec.get("proceeds_usd"),
                        rec.get("gain_loss_usd"),
                    ]
                )
        return buf.getvalue()

    def sync_from_capital_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Hook for capital audit chain events."""
        action = event.get("action", "")
        if action == "deposit":
            lot = self.record_acquisition(
                asset=str(event.get("asset", "USDC")),
                quantity=float(event.get("amount", 0)),
                cost_basis_usd=float(event.get("amount_usd", event.get("amount", 0))),
                source="capital_deposit",
                tx_ref=str(event.get("tx_hash", "")),
            )
            return {"synced": True, "lot_id": lot.lot_id}
        if action == "withdraw":
            disposals = self.record_disposal_fifo(
                asset=str(event.get("asset", "USDC")),
                quantity=float(event.get("amount", 0)),
                proceeds_usd=float(event.get("amount_usd", event.get("amount", 0))),
                tx_ref=str(event.get("request_id", "")),
            )
            return {"synced": True, "disposals": len(disposals)}
        return {"synced": False, "reason": "unsupported action"}
