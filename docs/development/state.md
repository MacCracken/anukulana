# anukulana — Current State

> **Last refresh**: 2026-07-01 | **Cadence**: every release.
> `CLAUDE.md` is preferences/process; this file is volatile state.

## Version

**0.1.0 — unreleased.** **M0: buildable scaffold** for the Type-3 pretrained-import
reference binary. `src/main.cyr` prints usage/version; builds + 1 test green. No
importer/forward yet — those are M1 (tula I/O) and M2 (import+run).

No released tags yet.

## Toolchain

Cyrius pin **6.3.27** (`cyrius.cyml`). Deps: **stdlib-only** at M0. M1 wires
`tula`; M2 wires `rupantara` + `rosnet` + `akshara` + `math` (see the commented
block in `cyrius.cyml`).

## Build artifacts

- `src/main.cyr` → `build/anukulana` (the reference binary; no distlib).
- CI + release workflows in `.github/workflows/`. `cyrius.lock` gitignored.

## Cross-repo status

- **tula** — released 0.1.0 (format ready). anukulana **M1 is unblocked**.
- **rupantara** — scaffolded (forward is its M1). anukulana **M2 gated on it**.
- **rosnet / akshara** — exist.

## Next

**M1** — consume tula: an `inspect`/`run` subcommand that opens a tula file,
enumerates tensors, verifies signatures. See `roadmap.md`.
