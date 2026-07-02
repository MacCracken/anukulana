# Changelog

All notable changes to `anukulana` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); SemVer (pre-1.0 — surface still
moving, no API freeze until v1.0).

## [0.1.0] — Unreleased

**M0 — buildable scaffold.** Repo skeleton for the Type-3 pretrained-import
reference binary.

### Added
- Scaffold: `cyrius.cyml` (binary; pin 6.3.27, stdlib-only), `src/lib.cyr`
  include chain, `src/version.cyr`, `src/main.cyr` (prints usage/version),
  `tests/tcyr/smoke.tcyr` (1 assertion), CI + release workflows, docs (ADR 0001
  scope, roadmap, state), README/CHANGELOG/CLAUDE/LICENSE/Makefile.

### Notes
- The importer/forward/LoRA/QLoRA land per `docs/development/roadmap.md`. M1
  wires `tula`; M2 wires `rupantara` + `rosnet` + `akshara` + `math` and imports
  a real GPT-2-small checkpoint to matching logits (the fidelity gate).
