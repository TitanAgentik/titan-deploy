# TITANHOME BIOS Checklist — WRX90E-SAGE SE + 9995WX

Use local keyboard/monitor or ASUS AST2600 BMC (PiKVM removed from BOM). Check each box in BIOS before Ubuntu install.

## Before first power-on

- [ ] Latest BIOS downloaded from ASUS WRX90E-SAGE SE support page
- [ ] USB Flashback done if recommended for 9995WX (see Level1Techs thread)
- [ ] Only Micron 7500 installed for first boot (optional — reduces variables)
- [ ] GPU0 in CPU-direct PCIe x16 slot, GPU1 in second x16
- [ ] TPM-SPI module installed
- [ ] XE360-TR5 pump connected to AIO_PUMP or CPU_FAN header

## BIOS navigation (ASUS workstation BIOS)

Press **Del** or **F2** at POST. Advanced Mode (F7) for most settings.

### EzFlash / BIOS version

- [ ] Note current BIOS version: _______________
- [ ] Update if not latest (Tool → ASUS EZ Flash)

### Ai Tweaker / Memory

| Setting | Target | Done |
|---------|--------|------|
| ECC Mode | Enabled | [ ] |
| EXPO / R-DIMM profile | EXPO I or DDR5-6000 CL36 | [ ] |
| Memory Context Restore | Enabled | [ ] |
| Power Down Enable | Disabled | [ ] |

If POST fails: clear CMOS, boot at JEDEC (4800), then enable EXPO.

### Advanced → AMD CBS / CPU

| Setting | Target | Done |
|---------|--------|------|
| SMT | Enabled | [ ] |
| Core Performance Boost | Auto (stock first) | [ ] |
| PBO | Disabled (tune later) | [ ] |

### Advanced → PCI Subsystem Settings

| Setting | Target | Done |
|---------|--------|------|
| Above 4G Decoding | **Enabled** | [ ] |
| Re-Size BAR Support | **Enabled** | [ ] |
| SR-IOV | Enabled | [ ] |
| PCIe Link Speed | Gen5 / Auto | [ ] |

### Advanced → NVMe / Storage

- [ ] Micron 7500 visible as boot device
- [ ] WD SN8100 drives visible (install OS on Micron only first)

### Boot

| Setting | Target | Done |
|---------|--------|------|
| Fast Boot | **Disabled** | [ ] |
| CSM | **Disabled** | [ ] |
| Secure Boot | **Disabled** (Ubuntu install) | [ ] |
| Boot Option #1 | Ubuntu USB (install) → then Micron NVMe | [ ] |

### Advanced → Trusted Computing

| Setting | Target | Done |
|---------|--------|------|
| TPM Device | Enabled | [ ] |
| TPM State | Enabled | [ ] |

### Advanced → CPU Configuration / SVM

| Setting | Target | Done |
|---------|--------|------|
| SVM Mode (AMD-V) | Enabled | [ ] |
| IOMMU | Enabled | [ ] |

### Trading Latency Profile (enable before live capital)

| Setting | Target | Done |
|---------|--------|------|
| Global C-state Control | **Disabled** | [ ] |
| CPU C-States | **Disabled** (re-enable for maintenance windows) | [ ] |
| CPPC Preferred Cores | Enabled | [ ] |
| Power Supply Idle Control | Typical Current Idle | [ ] |
| Package Power Limit | Auto (stock) | [ ] |

> **Note:** Disabling C-states increases idle power ~50–80W but removes 50–200µs wake latency on critical threads. Re-enable when not trading.

### Advanced → Onboard Devices

- [ ] Primary display: PCIe slot with GPU0 (or auto)
- [ ] Serial / parallel: disabled if unused

### Power

| Setting | Target | Done |
|---------|--------|------|
| ErP Ready | Disabled | [ ] |
| Restore on AC Power Loss | Power Off | [ ] |

### Q-Fan / Monitor

- [ ] AIO pump: full speed or performance profile
- [ ] Chassis fans: performance curve (GPU load will be high)
- [ ] Set BIOS administrator password: [ ]

## POST verification screen (note BIOS screenshot / BMC capture)

- [ ] CPU: AMD Ryzen Threadripper PRO 9995WX
- [ ] RAM: ~512 GB (503–512 GiB usable is normal)
- [ ] GPU0 + GPU1 detected in PCIe info
- [ ] Storage: 3 NVMe drives
- [ ] No Q-code errors (consult manual if stuck on 00, 15, etc.)

## Save

- [ ] F10 → Save & Reset
- [ ] First boot after EXPO may take 5–8 minutes — do not power off