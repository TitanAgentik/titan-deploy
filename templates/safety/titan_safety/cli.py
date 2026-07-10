#!/usr/bin/env python3
"""TITAN safety CLI — kill switch, promotion gate, heartbeat."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .allocator import AllocatorConfig, CapitalAllocator, LaneEdge
from .quantum_inspired import QiConfig, compare_to_kelly, optimize_lanes, synthetic_demo_lanes
from .audit_chain import AuditChainWriter, DecisionLogEntry, VersionFingerprint, build_fingerprint
from .auth import sign_control_command
from .capital import CapitalManager, load_capital_config
from .dead_mans_switch import DeadMansSwitch
from .execution_gate import ExecutionGate
from .kill_switch import KillSwitch
from .promotion_gate import PromotionCategory, PromotionGate, PromotionRequest
from .promotion_stats import StatsGateConfig, StrategyStats, StrategyStatsGate
from .flash_loan_router import FlashLoanConfig, FlashLoanRequest, FlashLoanRouter
from .flash_loan_sim import run_simulation as run_flash_loan_simulation
from .memecoin_filter import MemecoinFilter, MemecoinFilterConfig, MintCandidate
from .memecoin_sim import run_simulation
from .policy_loader import load_policy
from .profit_loop import ProfitLoop
from .tca import Fill, TCAEngine
from .telegram_capital import format_telegram_response, handle_capital_command
from .wind_down import WindDownController


def cmd_kill_activate(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    if args.signed:
        ok, msg = ks.verify_signed_command(args.signed)
        if not ok:
            print(json.dumps({"error": msg}))
            return 1
        if msg != "HALT":
            print(json.dumps({"error": f"unexpected command: {msg}"}))
            return 1
    state = ks.activate(args.operator, args.reason, flatten=not args.no_flatten)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_kill_deactivate(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    # Require signed RESUME — unsigned deactivate is a production vulnerability
    if not args.signed:
        print(json.dumps({"error": "signed RESUME required for deactivate", "hint": "titan-safety kill sign --command RESUME"}))
        return 1
    ok, msg = ks.verify_signed_command(args.signed)
    if not ok:
        print(json.dumps({"error": msg}))
        return 1
    if msg != "RESUME":
        print(json.dumps({"error": f"expected RESUME command, got '{msg}'"}))
        return 1
    state = ks.deactivate(args.operator)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_kill_status(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ks.health(), indent=2))
    return 0


def cmd_kill_sign(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    signed = ks.sign_command(args.command, args.operator)
    print(signed)
    return 0


def cmd_promotion_approve(args: argparse.Namespace) -> int:
    gate = PromotionGate(Path(args.safety_dir) if args.safety_dir else None)
    req = PromotionRequest(
        request_id=args.request_id,
        category=args.category,
        subject=args.subject,
        operator_response=args.response,
        operator_id=args.operator,
        metadata=json.loads(args.metadata) if args.metadata else {},
    )
    decision = gate.evaluate(req)
    print(json.dumps(decision.to_dict(), indent=2))
    return 0 if decision.approved else 1


def cmd_promotion_verify_audit(args: argparse.Namespace) -> int:
    gate = PromotionGate(Path(args.safety_dir) if args.safety_dir else None)
    ok, msg = gate.verify_audit_chain()
    print(json.dumps({"valid": ok, "message": msg}))
    return 0 if ok else 1


def cmd_heartbeat(args: argparse.Namespace) -> int:
    dms = DeadMansSwitch()
    state = dms.heartbeat(args.operator)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_audit_append(args: argparse.Namespace) -> int:
    fp = build_fingerprint(
        Path(args.model) if args.model else None,
        Path(args.lora) if args.lora else None,
        args.prompt_version,
        Path(args.soul) if args.soul else None,
    )
    entry = DecisionLogEntry(
        decision_id=args.decision_id,
        agent_id=args.agent,
        action=args.action,
        fingerprint=fp,
        payload=json.loads(args.payload) if args.payload else {},
    )
    writer = AuditChainWriter(Path(args.log))
    record = writer.append(entry)
    print(json.dumps(record, indent=2))
    return 0


def cmd_audit_verify(args: argparse.Namespace) -> int:
    writer = AuditChainWriter(Path(args.log))
    ok, msg = writer.verify()
    print(json.dumps({"valid": ok, "message": msg}))
    return 0 if ok else 1


def _capital_manager(args: argparse.Namespace) -> CapitalManager:
    cfg_path = getattr(args, "config", None)
    return CapitalManager(load_capital_config(cfg_path) if cfg_path else None)


def cmd_capital_deposit(args: argparse.Namespace) -> int:
    mgr = _capital_manager(args)
    result = mgr.deposit(
        args.amount,
        args.asset,
        chain=args.chain,
        tx_hash=args.tx_hash,
        source=args.source,
        operator=args.operator,
    )
    if args.telegram:
        print(format_telegram_response(result))
    else:
        print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_capital_withdraw(args: argparse.Namespace) -> int:
    mgr = _capital_manager(args)
    # Withdrawals require explicit --confirm-yes for amounts > 0 (production hardening)
    if not args.confirm and args.amount and args.amount > 0:
        if not getattr(args, "confirm_yes", False):
            print(json.dumps({
                "error": "withdrawal requires --confirm-yes (or --confirm REQUEST_ID for pending)",
                "ok": False,
            }))
            return 1
    if args.confirm:
        result = mgr.withdraw(
            0.0,
            args.asset,
            operator=args.operator,
            confirm_request_id=args.confirm,
        )
    else:
        result = mgr.withdraw(
            args.amount,
            args.asset,
            address=args.address,
            operator=args.operator,
        )
    if args.telegram:
        print(format_telegram_response(result))
    else:
        print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_auth_sign(args: argparse.Namespace) -> int:
    token = sign_control_command(args.command, args.operator, Path(args.safety_dir) if args.safety_dir else None)
    print(token)
    return 0


def cmd_gate_check(args: argparse.Namespace) -> int:
    from .kernel import TradeRequest
    from .policy_loader import load_policy

    policy = load_policy(args.policy)
    gate = ExecutionGate(policy, safety_dir=Path(args.safety_dir) if args.safety_dir else None)
    trade = TradeRequest.from_dict(json.loads(args.trade))
    believed = json.loads(args.believed) if args.believed else []
    decision = gate.gate(trade, believed, fast_path=True if args.fast else None)
    print(json.dumps(decision.to_dict(), indent=2))
    return 0 if decision.allowed else 1


def cmd_bft_vote(args: argparse.Namespace) -> int:
    from .trade_verifier import sign_bft_vote

    vote = sign_bft_vote(
        args.voter,
        args.trade_id,
        args.decision,
        float(args.confidence),
        safety_dir=Path(args.safety_dir) if args.safety_dir else None,
    )
    print(json.dumps(vote, indent=2))
    return 0


def cmd_gate_sign(args: argparse.Namespace) -> int:
    """Gate check then in-process sign if ALLOW (agent-autonomous path).

    Default: SigningNode in the same process (no :19010 hop).
    Legacy: ``--signing-mode http`` or ``--signing-endpoint`` POSTs to HTTP.
    """
    from .gate_receipt import RECEIPT_HEADER
    from .kernel import TradeRequest
    from .policy_loader import load_policy
    from .signing_service import (
        build_signing_node,
        resolve_signing_mode,
    )

    policy = load_policy(args.policy)
    safety = Path(args.safety_dir) if args.safety_dir else Path.home() / ".openclaw" / "safety"
    trade_data = json.loads(args.trade)
    trade = TradeRequest.from_dict(trade_data)
    believed = json.loads(args.believed) if args.believed else []
    decision = ExecutionGate(policy, safety_dir=safety).gate(
        trade, believed, fast_path=True if getattr(args, "fast", False) else None
    )
    if not decision.allowed:
        print(json.dumps({"gate": decision.to_dict(), "signed": False}, indent=2))
        return 1
    body: dict[str, Any] = {
        "request_id": trade.trade_id,
        "trade": trade_data,
        "gate_receipt": decision.receipt,
    }
    if args.calldata:
        body["calldata"] = args.calldata
    if args.typed_data:
        body["typed_data"] = json.loads(args.typed_data)

    mode = getattr(args, "signing_mode", None) or resolve_signing_mode(policy.raw or {})
    endpoint = (getattr(args, "signing_endpoint", None) or "").strip()
    if mode == "http":
        import urllib.error
        import urllib.request

        url = (endpoint or "http://127.0.0.1:19010").rstrip("/")
        req = urllib.request.Request(
            f"{url}/v1/sign",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                RECEIPT_HEADER: decision.receipt,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(args.timeout)) as resp:
                signed = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            signed = json.loads(exc.read().decode()) if exc.fp else {"error": str(exc)}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            signed = {"error": str(exc), "decision": "DENY"}
        signed.setdefault("mode", "http_legacy")
    else:
        node = build_signing_node(
            policy_path=Path(args.policy),
            safety_dir=safety,
            require_live_signer=False,
        )
        _code, signed = node.sign(body, {RECEIPT_HEADER: decision.receipt})
        signed.setdefault("mode", "in_process")
    print(json.dumps({"gate": decision.to_dict(), "signing": signed}, indent=2))
    return 0 if signed.get("decision") == "ALLOW" else 1


def cmd_capital_balance(args: argparse.Namespace) -> int:
    mgr = _capital_manager(args)
    bal = mgr.balance()
    if args.telegram:
        result = handle_capital_command("/balance", operator=args.operator, manager=mgr)
        print(format_telegram_response(result))
    else:
        print(json.dumps(bal, indent=2))
    return 0


def cmd_capital_sweep(args: argparse.Namespace) -> int:
    mgr = _capital_manager(args)
    result = mgr.sweep(
        weekly_profit_usd=args.weekly_profit,
        operator=args.operator,
    )
    if args.telegram:
        print(format_telegram_response(result))
    else:
        print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_kill_pipeline_halt(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    payload = ks.activate_pipeline(args.pipeline, args.operator, args.reason)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_kill_pipeline_resume(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    ok = ks.deactivate_pipeline(args.pipeline)
    print(json.dumps({"pipeline": args.pipeline, "resumed": ok}))
    return 0 if ok else 1


def cmd_kill_portfolio(args: argparse.Namespace) -> int:
    ks = KillSwitch(Path(args.safety_dir) if args.safety_dir else None)
    state = ks.activate_portfolio(args.operator, args.reason, flatten=not args.no_flatten)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_wind_down_safe_mode(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    state = wd.enter_safe_mode(args.operator, args.reason)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_wind_down_derisk(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    state = wd.start_derisk(args.operator, args.reason, current_pct=args.exposure_pct)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_wind_down_flatten(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    state = wd.start_flatten(args.operator, args.reason, current_pct=args.exposure_pct)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_wind_down_step(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    result = wd.step(current_exposure_pct=args.exposure_pct)
    print(json.dumps(result, indent=2))
    return 0


def cmd_wind_down_resume(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    state = wd.resume_normal(args.operator)
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def cmd_wind_down_status(args: argparse.Namespace) -> int:
    wd = WindDownController(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(wd.health(), indent=2))
    return 0


def cmd_telegram_capital(args: argparse.Namespace) -> int:
    result = handle_capital_command(args.text, operator=args.operator)
    print(format_telegram_response(result))
    return 0 if result.ok else 1


def cmd_notify_test(args: argparse.Namespace) -> int:
    from .telegram_notify import (
        format_institutional_message,
        load_config,
        notify,
        sample_test_event,
        send_telegram_message,
        TelegramConfig,
    )

    ev = sample_test_event()
    text = format_institutional_message(ev)
    if args.format_only:
        print(text)
        return 0
    if args.queue:
        result = notify(ev, safety_dir=Path(args.safety_dir) if args.safety_dir else None, send=not args.no_send)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    cfg = load_config()
    if args.dry_run:
        cfg = TelegramConfig(
            bot_token=cfg.bot_token or "dry",
            chat_id=cfg.chat_id or "0",
            enabled=True,
            dry_run=True,
        )
    send_result = send_telegram_message(text, config=cfg)
    print(text)
    print(json.dumps({"send": send_result}, indent=2))
    return 0 if send_result.get("ok") else 1


def cmd_notify_send(args: argparse.Namespace) -> int:
    from .telegram_notify import NotifyEvent, notify

    details: dict[str, Any] = {}
    if args.details_json:
        details = json.loads(args.details_json)
    ev = NotifyEvent(
        name=args.title,
        event_type=args.event_type,
        severity=args.severity,
        agent_id=args.agent_id,
        description=args.description,
        details=details,
        action_required=args.action_required or "",
        reason_codes=[c.strip() for c in args.reason_codes.split(",") if c.strip()],
    )
    result = notify(
        ev,
        safety_dir=Path(args.safety_dir) if args.safety_dir else None,
        send=not args.no_send,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_notify_drain(args: argparse.Namespace) -> int:
    from .telegram_notify import process_herald_queue

    results = process_herald_queue(
        Path(args.safety_dir) if args.safety_dir else None,
        max_items=args.max_items,
    )
    print(json.dumps({"drained": len(results), "results": results}, indent=2))
    return 0


def cmd_capital_verify_audit(args: argparse.Namespace) -> int:
    mgr = _capital_manager(args)
    ok, msg = mgr.verify_audit()
    print(json.dumps({"valid": ok, "message": msg}))
    return 0 if ok else 1


def cmd_allocator_plan(args: argparse.Namespace) -> int:
    lanes_raw = json.loads(args.lanes) if args.lanes else []
    lanes = [
        LaneEdge(
            pipeline_id=str(l.get("pipeline_id", "")),
            net_bps=float(l.get("net_bps", 0.0)),
            return_std=float(l.get("return_std", 0.0)),
            trade_count=int(l.get("trade_count", 0)),
            capacity_usd=float(l.get("capacity_usd", 0.0)),
            decaying=bool(l.get("decaying", False)),
            cluster=str(l.get("cluster", "")),
        )
        for l in lanes_raw
    ]
    allocator = CapitalAllocator()
    plan = allocator.allocate(
        args.equity, lanes, regime=args.regime, drawdown_pct=args.drawdown_pct
    )
    print(json.dumps(plan.to_dict(), indent=2))
    return 0


def cmd_promotion_stats(args: argparse.Namespace) -> int:
    raw = json.loads(args.stats)
    stats = StrategyStats(
        strategy_id=str(raw.get("strategy_id", "")),
        returns=[float(r) for r in raw.get("returns", [])],
        trials=int(raw.get("trials", 1)),
        sr_variance=raw.get("sr_variance"),
        num_trades=int(raw.get("num_trades", 0)),
        gross_bps=float(raw.get("gross_bps", 0.0)),
        cost_bps=float(raw.get("cost_bps", 0.0)),
        backtest_sharpe=float(raw.get("backtest_sharpe", 0.0)),
        shadow_sharpe=float(raw.get("shadow_sharpe", 0.0)),
    )
    result = StrategyStatsGate().evaluate(stats)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.passed else 1


def cmd_evolution_freeze(args: argparse.Namespace) -> int:
    from .evolution_freeze import EvolutionFreeze

    ef = EvolutionFreeze(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ef.freeze(args.operator, args.reason), indent=2))
    return 0


def cmd_evolution_unfreeze(args: argparse.Namespace) -> int:
    from .evolution_freeze import EvolutionFreeze

    ef = EvolutionFreeze(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ef.unfreeze(args.operator, args.reason), indent=2))
    return 0


def cmd_evolution_status(args: argparse.Namespace) -> int:
    from .evolution_freeze import EvolutionFreeze

    ef = EvolutionFreeze(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ef.status(), indent=2))
    return 0


def cmd_security_status(args: argparse.Namespace) -> int:
    from .security_ops import SecurityOps

    ops = SecurityOps(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ops.status(), indent=2))
    return 0


def cmd_security_layer(args: argparse.Namespace) -> int:
    from .security_ops import SecurityOps

    ops = SecurityOps(Path(args.safety_dir) if args.safety_dir else None)
    print(json.dumps(ops.layer_check(args.layer), indent=2))
    return 0


def cmd_security_honeypot(args: argparse.Namespace) -> int:
    from .security_ops import SecurityOps

    ops = SecurityOps(Path(args.safety_dir) if args.safety_dir else None)
    if args.hp_cmd == "arm":
        print(json.dumps(ops.honeypot_arm(args.operator), indent=2))
    elif args.hp_cmd == "disarm":
        print(json.dumps(ops.honeypot_disarm(args.operator), indent=2))
    else:
        print(json.dumps(ops.honeypot_status(), indent=2))
    return 0


def cmd_security_lockdown(args: argparse.Namespace) -> int:
    from .security_ops import SecurityOps

    ops = SecurityOps(Path(args.safety_dir) if args.safety_dir else None)
    result = ops.lockdown(
        args.operator,
        args.reason,
        dry_run=args.dry_run,
        signed=args.signed,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", False) else 1


def cmd_flashloan_route(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = FlashLoanConfig.from_raw(policy.raw if policy else {})
    router = FlashLoanRouter(cfg)
    decision = router.route(args.asset, args.amount_usd, args.chain, prefer=args.prefer or "")
    print(json.dumps(decision.to_dict(), indent=2))
    return 0


def cmd_flashloan_compose(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = FlashLoanConfig.from_raw(policy.raw if policy else {})
    router = FlashLoanRouter(cfg)
    raw = json.loads(args.request_json)
    req = FlashLoanRequest.from_dict(raw)
    result = router.compose(req)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.passed else 1


def cmd_flashloan_sim(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = FlashLoanConfig.from_raw(policy.raw if policy else {})
    result = run_flash_loan_simulation(
        count=args.count,
        seed=args.seed,
        equity_usd=args.equity,
        config=cfg,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_flashloan_status(args: argparse.Namespace) -> int:
    from .promotion_gate import PromotionGate

    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    fl = (policy.raw.get("flash_loan_live") or {}) if policy else {}
    pg = PromotionGate()
    print(
        json.dumps(
            {
                "enabled": bool(fl.get("enabled", False)),
                "requires_approval": bool(
                    (policy.raw.get("position_limits") or {}).get("flash_loan_live_requires_approval", True)
                ),
                "max_amount_usd": fl.get("max_amount_usd"),
                "pipeline_ids": fl.get("pipeline_ids", []),
                "promotion_approved": pg.has_approved("flash_loan_live"),
                "sources": fl.get("sources", {}),
            },
            indent=2,
        )
    )
    return 0


def cmd_promotion_list(args: argparse.Namespace) -> int:
    gate = PromotionGate()
    rows = gate.list_approvals()
    if args.approved_only:
        rows = [r for r in rows if r.get("approved")]
    print(json.dumps(rows, indent=2))
    return 0


def _memecoin_candidate_from_json(mint_json: str) -> MintCandidate:
    raw = json.loads(mint_json)
    fields = MintCandidate.__dataclass_fields__
    return MintCandidate(**{k: raw[k] for k in fields if k in raw})


def _lifecycle_phase(cand: MintCandidate, strategy: str) -> str:
    if cand.graduated or strategy == "post_grad_pullback":
        return "D"
    if strategy == "graduation" or cand.curve_progress_pct >= 85.0:
        return "C"
    if strategy == "curve_climb" or cand.curve_progress_pct >= 15.0:
        return "B"
    return "A"


def cmd_memecoin_filter(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = MemecoinFilterConfig.from_raw(policy.raw if policy else {})
    flt = MemecoinFilter(cfg)
    cand = _memecoin_candidate_from_json(args.mint_json)
    verdict = flt.evaluate(cand)
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0 if verdict.passed else 1


def cmd_memecoin_evaluate(args: argparse.Namespace) -> int:
    """Full JSON evaluate: filter verdict + lifecycle phase + capital envelope."""
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = MemecoinFilterConfig.from_raw(policy.raw if policy else {})
    flt = MemecoinFilter(cfg)
    cand = _memecoin_candidate_from_json(args.mint_json)
    verdict = flt.evaluate(cand)
    out = {
        "pipeline_id": "P22",
        "verdict": verdict.to_dict(),
        "lifecycle_phase": _lifecycle_phase(cand, verdict.recommended_strategy),
        "capital": {
            "max_snipe_pct_equity": cfg.max_snipe_pct_equity,
            "daily_sol_cap": cfg.daily_sol_cap,
            "envelope_usd": {"min": 100, "max": 2000},
        },
        "bft_vote_hint": "ALLOW" if verdict.passed and verdict.confidence >= 0.5 else (
            "ABSTAIN" if verdict.passed else "DENY"
        ),
        "live_gated": True,
        "note": "Catalog until promotion YES + memecoinTrench.enabled + capital_profile=live",
    }
    print(json.dumps(out, indent=2))
    return 0 if verdict.passed else 1


def cmd_memecoin_sim(args: argparse.Namespace) -> int:
    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    cfg = MemecoinFilterConfig.from_raw(policy.raw if policy else {})
    result = run_simulation(
        count=args.count,
        seed=args.seed,
        equity_usd=args.equity,
        config=cfg,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_memecoin_status(args: argparse.Namespace) -> int:
    from .adapters.jito_submit import JitoSubmitAdapter
    from .adapters.solana_recon import SolanaReconAdapter

    policy_path = Path(args.policy) if args.policy else Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"
    policy = load_policy(policy_path)
    m = (policy.raw.get("memecoin_trench") or {}) if policy else {}
    jito = JitoSubmitAdapter(str(m.get("jito_block_engine", "")))
    recon = SolanaReconAdapter(str(m.get("recon_module", "")))
    print(
        json.dumps(
            {
                "pipeline_id": "P22",
                "enabled": bool(m.get("enabled", False)),
                "jito": jito.health(),
                "recon": recon.health(),
                "daily_sol_cap": m.get("daily_sol_cap"),
                "max_snipe_pct_equity": m.get("max_snipe_pct_equity"),
            },
            indent=2,
        )
    )
    return 0


def _load_tca_engine(safety_dir: Path) -> TCAEngine:
    """Load TCAEngine; optionally hydrate from safety_dir/tca_fills.jsonl if present."""
    engine = TCAEngine()
    fills_path = safety_dir / "tca_fills.jsonl"
    if fills_path.exists():
        for line in fills_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            engine.ingest(
                Fill(
                    pipeline_id=str(raw.get("pipeline_id", raw.get("strategy_id", ""))),
                    venue=str(raw.get("venue", "")),
                    side=str(raw.get("side", "buy")),
                    notional_usd=float(raw.get("notional_usd", 0.0)),
                    expected_price=float(raw.get("expected_price", 0.0)),
                    realized_price=float(raw.get("realized_price", 0.0)),
                    gross_pnl_usd=float(raw.get("gross_pnl_usd", 0.0)),
                    gas_usd=float(raw.get("gas_usd", 0.0)),
                    tip_usd=float(raw.get("tip_usd", 0.0)),
                    reverted=bool(raw.get("reverted", False)),
                )
            )
    return engine


def cmd_tca_scorecard(args: argparse.Namespace) -> int:
    safety_dir = Path(args.safety_dir) if args.safety_dir else Path.home() / ".openclaw" / "safety"
    engine = _load_tca_engine(safety_dir)
    cards = engine.all_scorecards()
    summary = {
        "lanes_tracked": len(cards),
        "scorecards": [c.to_dict() for c in cards],
        "health": engine.health(),
        "note": "empty scorecard" if not cards else "loaded from safety dir" if (safety_dir / "tca_fills.jsonl").exists() else "in-memory",
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_tca_profit_loop(args: argparse.Namespace) -> int:
    safety_dir = Path(args.safety_dir) if args.safety_dir else Path.home() / ".openclaw" / "safety"
    engine = _load_tca_engine(safety_dir)
    loop = ProfitLoop(engine, safety_dir=safety_dir, auto_halt_bleeding=not args.dry_run)
    if args.dry_run:
        cards = engine.all_scorecards()
        bleeding = [c.pipeline_id for c in cards if c.verdict == "BLEEDING"]
        plan = CapitalAllocator().allocate(
            args.equity,
            [
                LaneEdge(
                    pipeline_id=c.pipeline_id,
                    net_bps=c.net_bps,
                    return_std=max(0.01, abs(c.net_bps) / 1e4 * 2),
                    trade_count=c.fill_count,
                    decaying=c.verdict == "BLEEDING" or c.decay_slope_bps < 0,
                )
                for c in cards
                if c.verdict != "INSUFFICIENT_DATA"
            ],
            regime=args.regime,
            drawdown_pct=args.drawdown_pct,
        )
        result = {
            "dry_run": True,
            "would_defund": bleeding,
            "already_defunded": sorted(loop.defunded_lanes()),
            "scorecards": [c.to_dict() for c in cards],
            "plan": plan.to_dict(),
            "notes": ["dry-run: no defund ledger writes, no pipeline halts"],
        }
        print(json.dumps(result, indent=2))
        return 0
    result = loop.run(
        equity_usd=args.equity,
        regime=args.regime,
        drawdown_pct=args.drawdown_pct,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def _lanes_from_json(lanes_raw: list[dict[str, Any]]) -> list[LaneEdge]:
    return [
        LaneEdge(
            pipeline_id=str(l.get("pipeline_id", "")),
            net_bps=float(l.get("net_bps", 0.0)),
            return_std=float(l.get("return_std", 0.0)),
            trade_count=int(l.get("trade_count", 0)),
            capacity_usd=float(l.get("capacity_usd", 0.0)),
            decaying=bool(l.get("decaying", False)),
            cluster=str(l.get("cluster", "")),
        )
        for l in lanes_raw
    ]


def cmd_qi_demo(args: argparse.Namespace) -> int:
    lanes = synthetic_demo_lanes()
    cfg = QiConfig(k=args.k, seed=args.seed)
    out: dict[str, Any] = {
        "demo": True,
        "lanes": [asdict(lane) for lane in lanes],
        "result": optimize_lanes(lanes, cfg).to_dict(),
    }
    if args.compare_kelly:
        out["comparison"] = compare_to_kelly(
            lanes,
            args.equity,
            qi_config=cfg,
            regime=args.regime,
            drawdown_pct=args.drawdown_pct,
        )
    print(json.dumps(out, indent=2))
    return 0


def cmd_qi_optimize(args: argparse.Namespace) -> int:
    lanes_raw = json.loads(args.lanes_json)
    lanes = _lanes_from_json(lanes_raw)
    cfg = QiConfig(
        k=args.k,
        seed=args.seed,
        sweeps=args.sweeps,
        risk_lambda=args.risk_lambda,
        cluster_penalty=args.cluster_penalty,
    )
    out: dict[str, Any] = {"result": optimize_lanes(lanes, cfg).to_dict()}
    if args.compare_kelly:
        out["comparison"] = compare_to_kelly(
            lanes,
            args.equity,
            qi_config=cfg,
            regime=args.regime,
            drawdown_pct=args.drawdown_pct,
        )
    print(json.dumps(out, indent=2))
    return 0


def cmd_edge_route(args: argparse.Namespace) -> int:
    from .edge_router import EdgeRouter

    router = EdgeRouter.from_path(Path(args.mesh) if args.mesh else None)
    decision = router.route(venue=args.venue or "", strategy_id=args.strategy or "")
    print(json.dumps(decision.to_dict(), indent=2))
    return 0


def cmd_edge_list(args: argparse.Namespace) -> int:
    from .edge_router import EdgeRouter

    router = EdgeRouter.from_path(Path(args.mesh) if args.mesh else None)
    print(json.dumps({"pops": router.list_pops(), "mode": router.mesh.get("mode")}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Safety CLI")
    parser.add_argument("--safety-dir", default=str(Path.home() / ".openclaw" / "safety"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_kill = sub.add_parser("kill", help="Kill switch commands")
    kill_sub = p_kill.add_subparsers(dest="kill_cmd", required=True)

    ka = kill_sub.add_parser("activate")
    ka.add_argument("--operator", default="cli")
    ka.add_argument("--reason", default="manual halt")
    ka.add_argument("--signed", help="HMAC-signed HALT command")
    ka.add_argument("--no-flatten", action="store_true")
    ka.set_defaults(func=cmd_kill_activate)

    kd = kill_sub.add_parser("deactivate")
    kd.add_argument("--operator", default="cli")
    kd.add_argument("--signed", default=None, help="HMAC-signed RESUME command (required)")
    kd.set_defaults(func=cmd_kill_deactivate)

    ks = kill_sub.add_parser("status")
    ks.set_defaults(func=cmd_kill_status)

    ksign = kill_sub.add_parser("sign")
    ksign.add_argument("--command", default="HALT")
    ksign.add_argument("--operator", default="operator")
    ksign.set_defaults(func=cmd_kill_sign)

    kpf = kill_sub.add_parser("portfolio")
    kpf.add_argument("--operator", default="cli")
    kpf.add_argument("--reason", default="portfolio halt")
    kpf.add_argument("--no-flatten", action="store_true")
    kpf.set_defaults(func=cmd_kill_portfolio)

    kp_pipe = kill_sub.add_parser("pipeline")
    pipe_sub = kp_pipe.add_subparsers(dest="pipe_cmd", required=True)
    ph = pipe_sub.add_parser("halt")
    ph.add_argument("--pipeline", required=True)
    ph.add_argument("--operator", default="cli")
    ph.add_argument("--reason", default="pipeline halt")
    ph.set_defaults(func=cmd_kill_pipeline_halt)
    pr = pipe_sub.add_parser("resume")
    pr.add_argument("--pipeline", required=True)
    pr.set_defaults(func=cmd_kill_pipeline_resume)

    p_wd = sub.add_parser("wind-down", help="Exit ramp / safe mode")
    wd_sub = p_wd.add_subparsers(dest="wd_cmd", required=True)
    wsm = wd_sub.add_parser("safe-mode")
    wsm.add_argument("--operator", default="cli")
    wsm.add_argument("--reason", default="safe mode")
    wsm.set_defaults(func=cmd_wind_down_safe_mode)
    wdr = wd_sub.add_parser("derisk")
    wdr.add_argument("--operator", default="cli")
    wdr.add_argument("--reason", default="derisk")
    wdr.add_argument("--exposure-pct", type=float, default=100.0)
    wdr.set_defaults(func=cmd_wind_down_derisk)
    wfl = wd_sub.add_parser("flatten")
    wfl.add_argument("--operator", default="cli")
    wfl.add_argument("--reason", default="flatten")
    wfl.add_argument("--exposure-pct", type=float, default=100.0)
    wfl.set_defaults(func=cmd_wind_down_flatten)
    wst = wd_sub.add_parser("step")
    wst.add_argument("--exposure-pct", type=float, default=None)
    wst.set_defaults(func=cmd_wind_down_step)
    wres = wd_sub.add_parser("resume")
    wres.add_argument("--operator", default="cli")
    wres.set_defaults(func=cmd_wind_down_resume)
    wstat = wd_sub.add_parser("status")
    wstat.set_defaults(func=cmd_wind_down_status)

    p_promo = sub.add_parser("promotion", help="Promotion gate")
    promo_sub = p_promo.add_subparsers(dest="promo_cmd", required=True)

    pa = promo_sub.add_parser("approve")
    pa.add_argument("--request-id", required=True)
    pa.add_argument("--category", choices=[c.value for c in PromotionCategory], required=True)
    pa.add_argument("--subject", required=True)
    pa.add_argument("--response", required=True, help="Must be YES for approval")
    pa.add_argument("--operator", default="operator")
    pa.add_argument("--metadata", default="")
    pa.set_defaults(func=cmd_promotion_approve)

    pv = promo_sub.add_parser("verify-audit")
    pv.set_defaults(func=cmd_promotion_verify_audit)

    pl = promo_sub.add_parser("list", help="List promotion audit records")
    pl.add_argument("--approved-only", action="store_true")
    pl.set_defaults(func=cmd_promotion_list)

    hb = sub.add_parser("heartbeat", help="Reset dead-man's switch timer")
    hb.add_argument("--operator", default="operator")
    hb.set_defaults(func=cmd_heartbeat)

    p_audit = sub.add_parser("audit", help="Decision log audit chain")
    audit_sub = p_audit.add_subparsers(dest="audit_cmd", required=True)

    aa = audit_sub.add_parser("append")
    aa.add_argument("--log", required=True)
    aa.add_argument("--decision-id", required=True)
    aa.add_argument("--agent", required=True)
    aa.add_argument("--action", required=True)
    aa.add_argument("--model")
    aa.add_argument("--lora")
    aa.add_argument("--prompt-version", default="v1")
    aa.add_argument("--soul")
    aa.add_argument("--payload", default="{}")
    aa.set_defaults(func=cmd_audit_append)

    av = audit_sub.add_parser("verify")
    av.add_argument("--log", required=True)
    av.set_defaults(func=cmd_audit_verify)

    p_cap = sub.add_parser("capital", help="Deposit, withdraw, balance, sweep")
    cap_sub = p_cap.add_subparsers(dest="cap_cmd", required=True)

    def _cap_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--operator", default="cli")
        p.add_argument("--telegram", action="store_true", help="HERALD-style output")
        p.add_argument("--config", help="Path to config.yaml or openclaw.json")

    cd = cap_sub.add_parser("deposit")
    _cap_common(cd)
    cd.add_argument("--amount", type=float, required=True)
    cd.add_argument("--asset", required=True)
    cd.add_argument("--chain", default=None)
    cd.add_argument("--tx-hash", default=None)
    cd.add_argument("--source", default="cli")
    cd.set_defaults(func=cmd_capital_deposit)

    cw = cap_sub.add_parser("withdraw")
    _cap_common(cw)
    cw.add_argument("--amount", type=float, default=0.0)
    cw.add_argument("--asset", default="USDC")
    cw.add_argument("--address", default=None)
    cw.add_argument("--confirm", default=None, help="Confirm pending request id")
    cw.add_argument("--confirm-yes", action="store_true", help="Explicit confirm for direct withdraw")
    cw.set_defaults(func=cmd_capital_withdraw)

    cb = cap_sub.add_parser("balance")
    _cap_common(cb)
    cb.set_defaults(func=cmd_capital_balance)

    cs = cap_sub.add_parser("sweep")
    _cap_common(cs)
    cs.add_argument("--weekly-profit", type=float, default=None)
    cs.set_defaults(func=cmd_capital_sweep)

    ct = cap_sub.add_parser("telegram")
    ct.add_argument("--text", required=True, help="Raw Telegram command e.g. /deposit 2500 USDC")
    ct.add_argument("--operator", default="telegram")
    ct.set_defaults(func=cmd_telegram_capital)

    cva = cap_sub.add_parser("verify-audit")
    cva.add_argument("--config", default=None)
    cva.set_defaults(func=cmd_capital_verify_audit)

    p_alloc = sub.add_parser("allocator", help="Capital allocation planning")
    alloc_sub = p_alloc.add_subparsers(dest="alloc_cmd", required=True)
    ap = alloc_sub.add_parser("plan")
    ap.add_argument("--equity", type=float, required=True)
    ap.add_argument("--regime", default="neutral")
    ap.add_argument("--drawdown-pct", type=float, default=0.0)
    ap.add_argument("--lanes", default="", help="JSON list of lane edge dicts")
    ap.set_defaults(func=cmd_allocator_plan)

    p_ps = sub.add_parser("promotion-stats", help="Evaluate statistical promotion gate")
    p_ps.add_argument("--stats", required=True, help="JSON StrategyStats payload")
    p_ps.set_defaults(func=cmd_promotion_stats)

    p_auth = sub.add_parser("auth", help="Control-plane HMAC tokens")
    auth_sub = p_auth.add_subparsers(dest="auth_cmd", required=True)
    asig = auth_sub.add_parser("sign")
    asig.add_argument("--command", required=True, help="e.g. FLATTEN, HEARTBEAT, TCA_INGEST")
    asig.add_argument("--operator", default="operator")
    asig.set_defaults(func=cmd_auth_sign)

    p_gate = sub.add_parser("gate", help="Unbypassable pre-trade execution gate")
    gate_sub = p_gate.add_subparsers(dest="gate_cmd", required=True)
    gc = gate_sub.add_parser("check")
    gc.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    gc.add_argument("--trade", required=True, help="JSON TradeRequest")
    gc.add_argument("--believed", default="", help="JSON list of believed positions")
    gc.add_argument("--fast", action="store_true", help="Millisecond hot path via /v1/fast_validate")
    gc.add_argument("--safety-dir", default="", help="~/.openclaw/safety for receipt secret")
    gc.set_defaults(func=cmd_gate_check)
    gs = gate_sub.add_parser(
        "sign",
        help="Gate check + in-process sign (autonomous path; no :19010 hop)",
    )
    gs.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    gs.add_argument("--trade", required=True, help="JSON TradeRequest incl. confidence + bft_votes")
    gs.add_argument("--believed", default="", help="JSON believed positions")
    gs.add_argument("--fast", action="store_true", help="Millisecond hot path via /v1/fast_validate")
    gs.add_argument("--calldata", default="", help="Hex calldata for live venues")
    gs.add_argument("--typed-data", default="", help="JSON EIP-712 typed_data for live venues")
    gs.add_argument(
        "--signing-mode",
        default=None,
        choices=["in_process", "http"],
        help="Default in_process; http = legacy :19010",
    )
    gs.add_argument(
        "--signing-endpoint",
        default="",
        help="Legacy HTTP endpoint when --signing-mode http (default http://127.0.0.1:19010)",
    )
    gs.add_argument("--safety-dir", default="")
    gs.add_argument("--timeout", default="5")
    gs.set_defaults(func=cmd_gate_sign)

    p_bft = sub.add_parser("bft", help="Advisory BFT vote tokens for trade authorization")
    bft_sub = p_bft.add_subparsers(dest="bft_cmd", required=True)
    bv = bft_sub.add_parser("vote")
    bv.add_argument("--voter", required=True, help="AUGUR|PREDATOR|ATLAS")
    bv.add_argument("--trade-id", required=True)
    bv.add_argument("--decision", default="ALLOW", choices=["ALLOW", "DENY"])
    bv.add_argument("--confidence", default="0.75")
    bv.add_argument("--safety-dir", default="")
    bv.set_defaults(func=cmd_bft_vote)

    p_evo = sub.add_parser("evolution", help="Freeze self-mod / evolution while live")
    evo_sub = p_evo.add_subparsers(dest="evo_cmd", required=True)
    efz = evo_sub.add_parser("freeze")
    efz.add_argument("--operator", default="cli")
    efz.add_argument("--reason", default="live capital")
    efz.set_defaults(func=cmd_evolution_freeze)
    euf = evo_sub.add_parser("unfreeze")
    euf.add_argument("--operator", default="cli")
    euf.add_argument("--reason", default="operator YES")
    euf.set_defaults(func=cmd_evolution_unfreeze)
    est = evo_sub.add_parser("status")
    est.set_defaults(func=cmd_evolution_status)

    p_sec = sub.add_parser("security", help="Four-pillar security ops")
    sec_sub = p_sec.add_subparsers(dest="sec_cmd", required=True)
    ss = sec_sub.add_parser("status")
    ss.set_defaults(func=cmd_security_status)
    sl = sec_sub.add_parser("layer-check")
    sl.add_argument("--layer", default=None, help="L1–L6 or omit for all")
    sl.set_defaults(func=cmd_security_layer)
    shp = sec_sub.add_parser("honeypot")
    hp_sub = shp.add_subparsers(dest="hp_cmd", required=True)
    hpa = hp_sub.add_parser("arm")
    hpa.add_argument("--operator", default="SENTINEL")
    hpa.set_defaults(func=cmd_security_honeypot)
    hpd = hp_sub.add_parser("disarm")
    hpd.add_argument("--operator", default="SENTINEL")
    hpd.set_defaults(func=cmd_security_honeypot)
    hps = hp_sub.add_parser("status")
    hps.set_defaults(func=cmd_security_honeypot)
    # honeypot status needs hp_cmd — set on parser
    hps.set_defaults(hp_cmd="status", func=cmd_security_honeypot)
    hpa.set_defaults(hp_cmd="arm", func=cmd_security_honeypot)
    hpd.set_defaults(hp_cmd="disarm", func=cmd_security_honeypot)
    sld = sec_sub.add_parser("lockdown")
    sld.add_argument("--operator", required=True)
    sld.add_argument("--reason", required=True)
    sld.add_argument("--dry-run", action="store_true")
    sld.add_argument("--signed", default=None)
    sld.set_defaults(func=cmd_security_lockdown)

    p_tca = sub.add_parser("tca", help="Transaction-cost analysis / profit loop")
    tca_sub = p_tca.add_subparsers(dest="tca_cmd", required=True)
    tsc = tca_sub.add_parser("scorecard", help="Print TCA scorecard summary")
    tsc.set_defaults(func=cmd_tca_scorecard)
    tpl = tca_sub.add_parser("profit-loop", help="Run TCA→allocator profit loop")
    tpl.add_argument("--dry-run", action="store_true", help="Plan only; no defund/halt side effects")
    tpl.add_argument("--equity", type=float, default=10000.0)
    tpl.add_argument("--regime", default="neutral")
    tpl.add_argument("--drawdown-pct", type=float, default=0.0)
    tpl.set_defaults(func=cmd_tca_profit_loop)

    p_edge = sub.add_parser("edge", help="5-PoP edge mesh routing (venue/strategy → PoP)")
    edge_sub = p_edge.add_subparsers(dest="edge_cmd", required=True)
    er = edge_sub.add_parser("route", help="Resolve target PoP for venue/strategy")
    er.add_argument("--venue", default="", help="Venue id (e.g. binance, jito_fra)")
    er.add_argument("--strategy", default="", help="Pipeline/strategy id (e.g. P22, P29)")
    er.add_argument("--mesh", default=None, help="Override edge_mesh.yaml path")
    er.set_defaults(func=cmd_edge_route)
    el = edge_sub.add_parser("list", help="List active PoPs and mesh mode")
    el.add_argument("--mesh", default=None, help="Override edge_mesh.yaml path")
    el.set_defaults(func=cmd_edge_list)

    p_fl = sub.add_parser("flashloan", help="Flash-loan router — route/compose/sim (ALCHEMY)")
    fl_sub = p_fl.add_subparsers(dest="fl_cmd", required=True)
    flr = fl_sub.add_parser("route", help="Select lowest-fee flash source for chain/asset")
    flr.add_argument("--asset", default="WETH")
    flr.add_argument("--amount-usd", type=float, required=True)
    flr.add_argument("--chain", default="ethereum")
    flr.add_argument("--prefer", default="", help="Preferred source (balancer, morpho, aave_v3, uniswap_v4)")
    flr.add_argument("--policy", default=None)
    flr.set_defaults(func=cmd_flashloan_route)
    flc = fl_sub.add_parser("compose", help="Compose flash-loan calldata + typed_data")
    flc.add_argument("--request-json", required=True, help="JSON FlashLoanRequest")
    flc.add_argument("--policy", default=None)
    flc.set_defaults(func=cmd_flashloan_compose)
    fls = fl_sub.add_parser("sim", help="Paper sim: route+compose profit distribution")
    fls.add_argument("--count", type=int, default=50)
    fls.add_argument("--seed", type=int, default=42)
    fls.add_argument("--equity", type=float, default=2500.0)
    fls.add_argument("--policy", default=None)
    fls.set_defaults(func=cmd_flashloan_sim)
    flst = fl_sub.add_parser("status", help="Flash-loan policy + promotion status")
    flst.add_argument("--policy", default=None)
    flst.set_defaults(func=cmd_flashloan_status)

    p_mc = sub.add_parser("memecoin", help="P22 memecoin trench filter / evaluate / sim / status")
    mc_sub = p_mc.add_subparsers(dest="mc_cmd", required=True)
    mcf = mc_sub.add_parser("filter", help="Run six-gate filter on mint JSON")
    mcf.add_argument("--mint-json", required=True, help="JSON MintCandidate fields")
    mcf.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    mcf.set_defaults(func=cmd_memecoin_filter)
    mce = mc_sub.add_parser("evaluate", help="Full JSON evaluate: gates + lifecycle + capital envelope")
    mce.add_argument("--mint-json", required=True, help="JSON MintCandidate fields")
    mce.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    mce.set_defaults(func=cmd_memecoin_evaluate)
    mcs = mc_sub.add_parser("sim", help="Paper sim: mock events → filter → TCA")
    mcs.add_argument("--count", type=int, default=100)
    mcs.add_argument("--seed", type=int, default=42)
    mcs.add_argument("--equity", type=float, default=2500.0)
    mcs.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    mcs.set_defaults(func=cmd_memecoin_sim)
    mcst = mc_sub.add_parser("status", help="P22 adapter / policy status")
    mcst.add_argument("--policy", default=str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"))
    mcst.set_defaults(func=cmd_memecoin_status)

    p_qi = sub.add_parser("qi", help="Quantum-inspired lane selection (offline classical SA)")
    qi_sub = p_qi.add_subparsers(dest="qi_cmd", required=True)
    qd = qi_sub.add_parser("demo", help="Synthetic P1/P5/P11/P12/P22/P29 lane demo")
    qd.add_argument("--seed", type=int, default=42)
    qd.add_argument("--k", type=int, default=4)
    qd.add_argument("--compare-kelly", action="store_true")
    qd.add_argument("--equity", type=float, default=10000.0)
    qd.add_argument("--regime", default="neutral")
    qd.add_argument("--drawdown-pct", type=float, default=0.0)
    qd.set_defaults(func=cmd_qi_demo)
    qo = qi_sub.add_parser("optimize", help="Optimize lane subset from JSON lane edges")
    qo.add_argument("--lanes-json", required=True, help="JSON list of lane edge dicts")
    qo.add_argument("--k", type=int, default=4)
    qo.add_argument("--seed", type=int, default=42)
    qo.add_argument("--sweeps", type=int, default=5000)
    qo.add_argument("--risk-lambda", type=float, default=1.0)
    qo.add_argument("--cluster-penalty", type=float, default=2.0)
    qo.add_argument("--compare-kelly", action="store_true")
    qo.add_argument("--equity", type=float, default=10000.0)
    qo.add_argument("--regime", default="neutral")
    qo.add_argument("--drawdown-pct", type=float, default=0.0)
    qo.set_defaults(func=cmd_qi_optimize)

    p_notify = sub.add_parser("notify", help="Institutional Telegram notifications (HERALD)")
    notify_sub = p_notify.add_subparsers(dest="notify_cmd", required=True)

    nt = notify_sub.add_parser("test", help="Send or preview a test notification")
    nt.add_argument("--format-only", action="store_true", help="Print formatted message only")
    nt.add_argument("--queue", action="store_true", help="Enqueue to herald_queue.jsonl")
    nt.add_argument("--no-send", action="store_true", help="Queue without Telegram API call")
    nt.add_argument("--dry-run", action="store_true", help="Skip Telegram API (dry run)")
    nt.add_argument("--safety-dir", default="", help="~/.openclaw/safety")
    nt.set_defaults(func=cmd_notify_test)

    ns = notify_sub.add_parser("send", help="Send a custom institutional notification")
    ns.add_argument("--title", required=True, help="Alert title / name")
    ns.add_argument("--event-type", required=True, help="e.g. risk_kernel_decision")
    ns.add_argument("--severity", default="INFO", choices=["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    ns.add_argument("--agent-id", default="HERALD")
    ns.add_argument("--description", required=True)
    ns.add_argument("--details-json", default="", help="JSON object for details block")
    ns.add_argument("--action-required", default="")
    ns.add_argument("--reason-codes", default="", help="Comma-separated reason codes")
    ns.add_argument("--no-send", action="store_true", help="Queue only")
    ns.add_argument("--safety-dir", default="")
    ns.set_defaults(func=cmd_notify_send)

    nd = notify_sub.add_parser("drain", help="Drain herald_queue.jsonl to Telegram")
    nd.add_argument("--safety-dir", default="")
    nd.add_argument("--max-items", type=int, default=50)
    nd.set_defaults(func=cmd_notify_drain)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
