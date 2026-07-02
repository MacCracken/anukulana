# anukulana — Current State

> **Last refresh**: 2026-07-01 | **Cadence**: every release.
> `CLAUDE.md` is preferences/process; this file is volatile state.

## Version

**0.1.0 — RELEASED 2026-07-02** (M0 scaffold + M1 consume-tula). **M2 in progress
(`[Unreleased]`):** **bite 1 — the foreign safetensors parser DONE** — `st_open`
parses `[u64 len][JSON header][data]` (header via **bayan**'s sovereign JSON DOM,
not hand-rolled) into a bounds-checked tensor directory; IEEE-754 f32/f16/bf16→f64
wideners; `st_read_f64`. `tests/tcyr/safetensors.tcyr` **30** green (wideners
bit-exact + parse round-trip + untrusted-buffer rejection); suite **39**. Next:
**bite 2** — GPT-2→rupantara layout mapping (fused-QKV split, Conv1D transpose via
ganita) → run `ru_model_fwd` → fidelity gate.

Released: **0.1.0**.

## Toolchain

Cyrius pin **6.3.27** (`cyrius.cyml`). Deps: **stdlib-only** at M0. M1 wires
`tula`; M2 wires `rupantara` + `rosnet` + `akshara` + `math` (see the commented
block in `cyrius.cyml`).

## Build artifacts

- `src/main.cyr` → `build/anukulana` (the reference binary; no distlib).
- CI + release workflows in `.github/workflows/`. `cyrius.lock` gitignored.

## Cross-repo status

- **tula** — released 1.0.0 (format frozen). anukulana **M1 DONE** (consumed).
- **rupantara** — released 0.4.0 (forward + KV-cache decode, parity-proven).
  anukulana **M2 UNBLOCKED**.
- **rosnet / akshara** — exist (M2 wires them).

## Next

**M2 — import + run (the headline):** parse a foreign **GPT-2-small safetensors**
(own parser, no libs) → map foreign tensor names/shapes onto rupantara's packed
layout (fp16/bf16 → f64) → run `ru_model_fwd` → logit-fidelity gate vs a reference.
Untrusted-parser hardening pulled forward. See `roadmap.md`.
