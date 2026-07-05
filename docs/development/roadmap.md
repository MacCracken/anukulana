# anukulana — Roadmap (march to v1.0)

> **For a secondary agent picking this up cold.** Self-contained plan. Read this
> + `CLAUDE.md` (conventions) + `docs/adr/0001-anukulana-scope.md` (scope).
> anukulana is the Type-3 pretrained-import **reference binary** — it consumes
> tula (format) / rupantara (forward) / rosnet (tensors) / akshara (tokenizer),
> and does not reinvent them. Pre-1.0: surface may move, no freeze until v1.0.

---

## Working agreement

- **Build/test:** `make build` (binary) · `make test` · pin in `cyrius.cyml`.
- **Binary layout:** `main()` only in `src/main.cyr`; `src/lib.cyr` is the shared
  include chain (stdlib + domain modules). New module → `src/lib.cyr` (order).
  Consumed libs wired in `cyrius.cyml [deps.*]` + included in `src/lib.cyr` at
  their milestone. LSP "undefined" across flat modules is expected.
- **Definition of done each bite:** `make test` green · `cyrius fmt` clean ·
  `cyrius lint` no `warn ` (**keep lines ≤120 — split long strings**) · CHANGELOG
  `[Unreleased]` updated.
- **Do NOT bump VERSION or git** — maintainer cuts releases; work under `[Unreleased]`.

## Discipline (from attn11)

Cyrius-native, no BLAS/libc/autodiff. **FD-gate any new gradient** (the LoRA A,B
path). The import is gated by a **logit-fidelity benchmark vs the reference
implementation** (fairness-ruled). Honest-negatives reported (small-scale import
fidelity, NF4 quant error).

---

## Shipped

- **M0 ✅** buildable scaffold (usage/version binary; `smoke.tcyr` 1).

---

## Cross-repo dependency order (read before sequencing)

```
tula (format, RELEASED 0.1.0) ──┐
rupantara (forward) ── M1 needed ┼──> anukulana M2 (import+run) needs BOTH
rosnet / akshara (exist) ───────┘
```
**anukulana M1 (consume tula) is unblocked now.** anukulana M2 (the forward/import
headline) is **gated on rupantara M1** (the transformer forward). Do M1 now;
M2 when rupantara's forward lands.

---

## Remaining milestones

### M1 — consume tula (weight-file I/O) ✅ DONE (2026-07-02)
- Wired `[deps.tula]` 1.0.0 + `[deps.sigil]` 3.9.9. `src/inspect.cyr`: `anuk_inspect`
  opens a tula file (`tula_read_file`, full validation), `anuk_enumerate` lists
  tensors (name/dtype/shape/bytes), `anuk_verify` checks the Ed25519 signature
  (and rejects a wrong key). `inspect` + `version` subcommands in `src/main.cyr`.
- **Acceptance MET:** `tests/tcyr/tula_io.tcyr` (8 assertions) builds+signs a
  checkpoint, reads it as untrusted, enumerates (2 tensors), verifies (OK +
  wrong-key rejected), payload-ok guard, bit-exact tensor round-trip; suite 1 → **9**
  green. CLI `anukulana inspect <file>` verified end-to-end; missing/malformed file
  fails cleanly (rc=1, no crash).

### M2 — import + run (THE headline) — ✅ COMPLETE 2026-07-04 (incl. the fidelity gate)
- **✅ Bite 1 — safetensors parser DONE (2026-07-02):** `src/safetensors.cyr`
  parses `[u64 len][JSON header][data]` → bounds-checked tensor directory. **The
  JSON header uses `bayan`** (the sovereign JSON DOM — the ecosystem lib, NOT a
  foreign dep and NOT hand-rolled). IEEE-754 f32/f16/bf16→f64 wideners (unhomed →
  candidate for rosnet). `tests/tcyr/safetensors.tcyr` 30 green (wideners bit-exact
  + full parse round-trip + untrusted-buffer rejection). Suite 9 → **39**.
  *("own parsers, no libs" clarified: no foreign safetensors/GGUF lib — but bayan
  IS the sovereign JSON parser; use it, don't reinvent.)*
- **✅ Bite 2 — GPT-2 → rupantara mapping DONE (2026-07-02):** `src/gpt2.cyr`
  (`anuk_gpt2_infer_cfg` + `anuk_gpt2_pack`, packing through rupantara's own
  `_ru_o_*`/`_p_*` offset helpers). **Weight convention verified vs rosnet source
  = `[in,out]` (GPT-2 Conv1D) ⇒ NO transpose** (nanoGPT transposes only for
  `nn.Linear`); the real remap is the **fused-QKV column split**, everything else a
  direct copy. `tests/tcyr/gpt2.tcyr` (10) — export→import round-trip with packed
  params **and** `ru_model_fwd` logits both **bit-identical** to the direct forward
  (bayan-built safetensors writer in the test). Suite 39 → **49**.
- **✅ Bite 3 — real GPT-2-small imports + runs cleanly (2026-07-02):** `gpt2` CLI
  on the real HF checkpoint (548 MB / 148 tensors, fp32) via mmap — config inferred
  (V=50257 C=768 NL=12), 0 NaN in 123.6 M widened params, batch fwd == KV-decode
  bit-identical, logits finite, ~3.7 s. First surfaced + fixed the `ganita_f64_tanh`
  NaN-overflow bug (ganita 1.0.2; cyrius 6.3.31 re-fold; pin bumped 6.3.27→6.3.31).
- **✅ Bite 4 — exact HF-fidelity gate (2026-07-04): M2 COMPLETE.** `gpt2-oracle`
  CLI + `src/oracle.cyr` gate the forward against a **committed HF-reference
  fixture** (`tests/fixtures/gpt2_oracle_v1.bin` — 3 deterministic 16-token
  sequences, per-position argmax + last-position logits, generated ONCE by
  `tests/oracle/gen_fixture.py` in a disposable torch venv; Python/torch is never
  a build/run/test dependency — the fixture is data). Result on the real
  checkpoint: **argmax exact at all 48 positions; last-row maxrel 1.05e-6 worst**
  (fp32-rounding scale — HF computes fp32, we compute f64 over the same widened
  weights, so bit-exact is impossible by construction and ~1e-6 is the expected
  gap). Gate frozen at **maxrel ≤ 1e-5** (10× above measured) + exact argmax +
  NaN-free. `make fidelity` runs it.
- **Acceptance (fidelity gate): ✅ MET** — logits match HF `from_pretrained` on
  fixed inputs within fp32-rounding tolerance, greedy stream identical. (The
  `docs/benchmarks.md` number lands with the M5 bench pass; the gate itself is
  the recorded artifact until then.)

### M3 — LoRA — ▶ bite 1 LANDED 2026-07-04 (head adapter; `[Unreleased]`)
- `W' = W + (α/r)·B·A`; A gaussian, B zero; gradients route **only** into A,B via
  two `rosnet.linear_bwd` passes (no new gradient op). ⚠ the naive
  `dL/dA = Bᵀ·dL/dZ` is wrong (omits the activation `Xᵀ`) — let `linear_bwd`
  supply it. **FD-gate the A,B path.** A fine-tune measurably adapts the base.
- **✅ Bite 1 — the primitive + head adapter:** `src/lora.cyr`
  (fwd/bwd/merge/xent/SGD/**Adam**) FD-gated entry-by-entry (dA + dB, rel <
  1e-5; suite 49→54) + `gpt2-lora` on the real checkpoint: **xent 10.79 →
  0.0000, argmax 1/8 → 8/8, base bit-frozen, adapter-off bit-identical.**
  Finding: plain SGD diverges on real-GPT-2 features (massive-activation
  outlier dims → `dA` explodes at any flat lr) — Adam is required, as in the
  LoRA paper. Head adapter stays UNMERGED (tied tok_emb).
- **Open scope question (bite 2?):** per-layer adapters (the paper's q/v
  placement) need a **backward chain** through the network tail (head → final
  LN → block internals) — machinery that lives in **attn11** (the training
  reference), not here. Options: (a) accept head-adapter as M3's
  measurable-adaptation proof and move to M4 QLoRA (quantization thesis,
  reuses this exact machinery), (b) hand-derive a minimal tail-chain
  (ln_bwd + head_bwd) for last-block adapters, (c) defer depth to attn11.
  **User call.**

### M4 — QLoRA / NF4
- 4-bit blockwise **NormalFloat** (block 64) + per-block absmax scale +
  **double-quant**; LoRA over the frozen NF4 base; dequant-on-the-fly. Store via
  tula's `nf4` dtype helpers (tula M2). **User-confirmed additive step.**
- **Acceptance:** NF4 pack→dequant error bounded; LoRA-over-NF4 fine-tune works.

### M5 — hardening + fuzz + bench
- Harden the **foreign parsers** (safetensors/GGUF are untrusted input — bounds/
  overflow/lying-header safe, reject malformed). Fuzz them. Bench import + forward
  → `docs/benchmarks.md`.

### M6 — security audit + SECURITY.md
- 6-dimension audit (memory safety · integer overflow · untrusted-parser bounds ·
  LoRA-gradient correctness · resource caps · fail-loud). Report + `SECURITY.md`.

### v1.0 — freeze & clean cut
- CLI + API frozen + `docs/api.md` + `STABILITY.md`; ≥1 downstream consumer/example
  (e.g. a served model via hoosh, or a documented import→adapt→save flow);
  maintainer bumps VERSION → 1.0.0 + tags.

---

## v1.0 criteria

- [ ] CLI/API frozen + documented (`docs/api.md` + `STABILITY.md`)
- [x] **GPT-2 import logit-fidelity gate** (matches reference) — the headline ✅ 2026-07-04 (`gpt2-oracle`, maxrel ≤ 1e-5 + exact argmax)
- [ ] LoRA FD-gated; QLoRA/NF4 working
- [ ] Foreign parsers hardened + fuzz clean; bench (`docs/benchmarks.md`)
- [ ] Security audit + `SECURITY.md`
- [ ] ≥1 downstream consumer/example green
- [ ] CHANGELOG complete; version consistency (CI docs gate)

---

## Gates / relations

- **Deps:** tula (format, released) · rupantara (forward — **M2 blocker**) ·
  rosnet (tensors + LoRA linears) · akshara (tokenizer) · math. CPU-f64 first;
  larger models want rosnet's mabda GPU profile (deferred).
- **Boundary:** NF4 import-quant is anukulana's; QAT-from-scratch is tentib's
  (`integer-native-ml.md`). Rotation-PTQ / one-shot-sparsity stay research-watch.
- **Ecosystem:** gap #1's importer — `type3-weight-import.md` + `software-port-path.md`.
