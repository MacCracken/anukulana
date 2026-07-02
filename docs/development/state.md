# anukulana — Current State

> **Last refresh**: 2026-07-01 | **Cadence**: every release.
> `CLAUDE.md` is preferences/process; this file is volatile state.

## Version

**0.1.0 — unreleased.** **M1: consume tula DONE** (2026-07-02) — `inspect` opens a
tula checkpoint, enumerates tensors (name/dtype/shape/bytes), and verifies its
Ed25519 signature (tamper-reject); `tests/tcyr/tula_io.tcyr` **9** green, CLI
verified end-to-end, malformed input fails cleanly. M0 scaffold underneath. Next:
**M2** — the foreign safetensors importer + forward on rupantara (**unblocked**:
rupantara released 0.4.0).

No released tags yet.

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
