# Agent Host Security Model

> **Scope:** TITANHOME + edge workers + Mac Mini vault metadata  
> **Goal:** Agent filesystem and LLM runtime cannot read control-plane secrets or signing material.

---

## Threat model

| Asset | Exposure if leaked | Mitigation |
|-------|-------------------|------------|
| Signing keys / TPM PCR | Unauthorized broadcasts | In-process SigningNode; separate UID; no agent read |
| `policy.yaml` | Kernel bypass attempts | Root-owned; agents read-only via kernel HTTP |
| Telegram / API tokens | Alert spoofing, data exfil | `titan-ops` env only; not in agent workspace |
| Trezor metadata | Sweep social engineering | Mac Mini airgap; ceremonies offline |

---

## Linux users (recommended layout)

| User | UID role | Capabilities |
|------|----------|--------------|
| `titan-ops` | Human operator + systemd services | Full control-plane; runs `:19001–:19008` |
| `titan-agent` | OpenClaw / Hermes agent runtime | **No** read on `/etc/titan/secrets`, `~/.openclaw/secrets/` |
| `titan-sign` | Optional dedicated signer (legacy `:19010`) | `CAP_IPC_LOCK` only if needed; no shell |
| `titan-edge` | Edge workers (stateless) | No LLM; no signing; outbound only to venues |

### Filesystem isolation

```text
/etc/titan/secrets/          root:titan-ops  0750   # TELEGRAM_*, RPC auth
~/.openclaw/risk_kernel/     root:titan-ops  0750   # policy.yaml — agents use HTTP API only
~/.openclaw/safety/          titan-ops       0750   # kill switch, promotion receipts
~/.openclaw/memory/          titan-agent     0750   # decision log (append via safety API)
~/.openclaw/workspace/       titan-agent     0755   # agent skills — no secrets
```

**Enforced rule:** `titan-agent` GID must not include `titan-ops` or `titan-sign`.

### systemd hardening (template)

```ini
[Service]
User=titan-agent
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/data/openclaw/memory
PrivateTmp=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
CapabilityBoundingSet=
```

Signing service (`titan-safety`) runs as `titan-ops` — colocated with gate, not agent UID.

---

## Linux capabilities

| Capability | Who | Why |
|------------|-----|-----|
| *(none extra)* | `titan-agent` | Default — no raw sockets beyond normal |
| `CAP_IPC_LOCK` | `titan-ops` (signing) | Pin signing memory if using TPM-SPI |
| `CAP_NET_BIND_SERVICE` | edge workers | Bind :443 on PoP only |

Do **not** grant `CAP_SYS_ADMIN`, `CAP_DAC_OVERRIDE`, or `CAP_BPF` to agent users.

---

## BusKill / hardware kill — live install checklist

> **Status:** Manual ops step — not wired in software bundle (`kill_switch.yaml`).

- [ ] BusKill cable (USB) connected TITANHOME → operator physical token
- [ ] udev rule triggers `systemctl stop titan-openclaw-gateway` + `titan-safety kill activate` on disconnect
- [ ] Test monthly alongside UPS drill
- [ ] Document cable serial in operator vault (not in git)
- [ ] Verify agent cannot disable udev rule without `titan-ops` sudo
- [ ] Mac Mini vault remains airgapped — BusKill on trading host only

**STUB:** Provide `scripts/ci/apply_agent_netns_policy.sh.stub` for network namespace isolation on demand.

---

## Network namespaces (optional STUB)

Edge agents should not reach `127.0.0.1:19001` directly — proposals go through OpenClaw gateway which calls kernel as `titan-ops`. Netns policy script documents split.

---

## Verification

```bash
# Agent must fail to read secrets
sudo -u titan-agent cat ~/.openclaw/secrets/telegram.env  # expect Permission denied
./verify.sh
python3 scripts/ci/check_doc_policy_consistency.py
```

---

## References

- `AGENTS.md` — Signing Isolation
- `docs/runbooks/host_compromise.md`
- `templates/playbooks/kill_switch.yaml`
