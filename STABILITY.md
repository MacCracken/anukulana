# anukulana — Stability Policy (1.x)

**v1.0.0 froze the public surface** documented in [`docs/api.md`](docs/api.md):
the CLI commands (names, arguments, gate semantics, exit codes) and the listed
module functions (signatures + contracts).

Guarantees for the 1.x line:

- **Frozen:** CLI commands and their gate semantics; the listed `st_*`, `gg_*`
  (1.1.0), `anuk_*`, `lora_*`, `nf4_*` signatures and the `ST_MAX_ELEMS` /
  `GG_MAX_ELEMS` caps (1.3.0); the checkpoint/adapter tensor names; the
  oracle-fixture format v1; the exit-code convention (0 = all gates pass, 1 = a
  gate failed or an argument is missing, 2 = an unknown command or option —
  1.2.2).
- **Additive-only minors:** new CLI commands (e.g. GGUF import), new module
  functions, new checkpoint tensors (readers tolerate extras), and inputs that
  were rejected before and are now accepted (1.6.0: GGUF's legacy block types).
- **Out of freeze:** `_`-prefixed internals; demo training hyperparameters
  (the gates are frozen, the knobs are not); wall-clock numbers in
  `docs/benchmarks.md` (re-captured per toolchain/hardware change).
- **Consumed-surface pins:** tula (format v1, frozen), rupantara `ru_*`
  (parity-proven vs attn11), rosnet 1.x (frozen), sigil Ed25519. Dep-pin bumps
  are patch-level unless a consumed surface breaks (which their own freezes
  forbid in their 1.x lines).

Breaking any of the frozen items requires a 2.0.0 with a migration note in the
CHANGELOG (Keep-a-Changelog **Breaking** section).
