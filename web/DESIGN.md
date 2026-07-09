# TITAN Cockpit — Design System

Original control-plane UI for the TITAN operator surface. Built for dense trading ops: signal clarity, low glare, and quick scanning under load.

## Principles

1. **Signal over decoration** — Cyan primary accent for active states; gold for operator attention; no borrowed product aesthetics.
2. **Control-room hierarchy** — Sora for headings, Source Sans 3 for UI, IBM Plex Mono for ports, timestamps, and labels.
3. **Cool slate canvas** — Light graphite surfaces (`#e8ecf2`) reduce eye strain vs pure white or warm cream.
4. **Navy status strip** — Dashboard KPI band uses a mesh-grid navy panel (not a flat black editorial block).
5. **Operator density** — Command palette (⌘K), breadcrumbs, activity rail, clickable metrics.

## Color tokens (light / Signal)

| Token | Hex | Usage |
|-------|-----|--------|
| `--titan-navy` | `#0b1528` | Primary text, status strip base |
| `--titan-surface` | `#e8ecf2` | Page background |
| `--titan-panel` | `#f4f6fa` | Sidebar, rails |
| `--titan-signal` | `#06b6d4` | Primary accent, links, active nav |
| `--titan-gold` | `#e8a317` | Secondary highlight, badges |
| `--titan-mint` | `#10b981` | Healthy / OK |
| `--titan-amber` | `#f59e0b` | Warning |
| `--titan-coral` | `#ef4444` | Halt / danger |

## Typography

| Role | Stack |
|------|--------|
| Display | `"Sora", system-ui, sans-serif` |
| UI | `"Source Sans 3", system-ui, sans-serif` |
| Data | `"IBM Plex Mono", ui-monospace, monospace` |

## Themes

| ID | Name | Description |
|----|------|-------------|
| `light` | Signal (default) | Cool slate light theme |
| `dark` | Night | Deep institutional dark with teal accent |

Switch in **Settings → Appearance**.
