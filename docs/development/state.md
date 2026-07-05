# anukulana — Current State

> **Last refresh**: 2026-07-05 | **Cadence**: every release.
> `CLAUDE.md` is preferences/process; this file is volatile state.

## Version

**1.1.1 — RELEASED 2026-07-05 (`--sk` operator-key signing — ifran Lane 2
closes).** `gpt2-tula … --sk <operator.sk>` signs the NF4 checkpoint + adapter
with a real 64 B seed||pk key file (ifran's `keys init` layout) instead of the
ephemeral demo key; `anuk_sk_load` is the loader (pk = sk+32). **End-to-end
proof with ifran 2.0.0**: fresh `keys init` → `gpt2-tula --sk` on the real
124M checkpoint → `ifran store add` records **`verified`** for both artifacts
(was `signed-unknown-key`) → `store verify` sig-verified. Suite **121→129**
(nf4_store 13→21). Behavior without the flag unchanged.

**1.1.0 — RELEASED 2026-07-05 (GGUF import — the named post-1.0 headline).**
`src/gguf.cyr` (sovereign GGUF v2/v3 parser — typed-KV structural skip,
ne-order dims, alignment handling, F32/F16 widen, quantized GGML rejects
cleanly; wrap-safe + null-checked per the audit's standing guidance) +
`src/gpt2_gguf.cyr` (GPT-2 `blk.N.*` mapping — ggml `[out,in]` **transposed
back** to rosnet's `[in,out]`, fused-qkv split, config from KV metadata) + CLI
`gpt2-gguf` / `gpt2-cross`. **Proof on the real 124M checkpoint: `gpt2-gguf`
batch==decode 0 diffs; `gpt2-cross` — both foreign doors BIT-IDENTICAL
(123,659,520 params / 402,056 logits, 0 diffs).** +38 asserts
(`tests/tcyr/gguf.tcyr`, in-test GGUF writer over exact-in-f32 seeds) + 35k
GGUF fuzz rounds (`fuzz.tcyr`); suite **80→121**. GGUF proof file generated
once by `tests/oracle/gen_gguf.py` (disposable venv: gguf+numpy+safetensors,
no torch). Next lanes: quantized GGML payloads · llama-arch (TinyLlama)
mapping.

**1.0.0 — RELEASED 2026-07-04 (STABLE — the Type-3 reference, frozen).** API
frozen (`docs/api.md` + `STABILITY.md`); parsers fuzz-gated
(`tests/tcyr/fuzz.tcyr`, 38k+ rounds, suite **80**); audit **PASS after 2
fixes** (both hostile-input DoS in `st_open`: header bounds-check integer-wrap
+ unchecked entry-table alloc — `docs/audit/2026-07-04-audit.md` +
`SECURITY.md`); benchmarks captured (`docs/benchmarks.md`). All seven v1.0
criteria met. **Post-1.0 headline: GGUF import.** Same-day prior releases:

**0.5.0 — RELEASED 2026-07-04 (M4 tail: signed NF4 persistence — the charter is
FULLY built).** `src/nf4.cyr` base codec reconciled to **delegate to tula's
shipped NF4** (the 0.4.0 hand-roll duplicated tula 1.0.0's frozen surface — the
"know the ecosystem" catch; only superblock-256 double-quant stays local) +
`src/nf4_store.cyr` (signed checkpoint/adapter save/load, Ed25519-verified,
wrong-key/tamper REJECTED) + `gpt2-tula` (real checkpoint: **63.8 MB signed NF4
file**, base + adapter both round-trip **bit-identical**, adapter trains over
the LOADED base, 8/8). Suite **75**. Cyrius gotcha: `match` is a reserved
keyword. Prior same-day releases:

**0.4.0 — RELEASED 2026-07-04 (M3 LoRA + M4 QLoRA/NF4 — the adapt arc).**
`src/lora.cyr` (FD-gated fwd/bwd/merge + xent + SGD/Adam) + `gpt2-lora` (head
adapter: xent 10.79→0.0000, argmax 8/8, base bit-frozen) + `src/nf4.cyr` (NF4
codec: blockwise-64, double-quant scales, 8-test exactness gate) + `gpt2-qlora`
(whole 124M base at 4 bits; adapter recovers 8/8 over it, codes bit-frozen;
honest 124M-scale drift reported). Suite **62**. Same-day prior releases:

**0.3.0 — RELEASED 2026-07-04 (M2 COMPLETE — the imported model matches HF
exactly).** The M2 arc landed across 0.2.0 + 0.3.0:

- **0.2.0 (2026-07-02)** — the foreign importer works on a real model: `st_open`
  safetensors parser (bayan JSON DOM, bounds-checked, untrusted-input safe) +
  IEEE-754 f32/f16/bf16→f64 wideners + the GPT-2→rupantara mapping (fused-QKV
  split, NO transpose — rosnet `linear_fwd` is Conv1D `[in,out]`) + mmap past the
  256 MB alloc cap. Real 124M checkpoint: config inferred (V=50257/C=768/NL=12),
  0 NaN in 123.6 M widened params, batch fwd == KV-cache decode bit-identical.
  Surfaced + fixed `ganita_f64_tanh` NaN-overflow (ganita 1.0.2 → cyrius 6.3.31
  re-fold → pin bump).
- **0.3.0 (2026-07-04)** — the exact HF-fidelity gate: `gpt2-oracle` +
  `src/oracle.cyr` vs a **committed HF-logits fixture**
  (`tests/fixtures/gpt2_oracle_v1.bin`; generated once by
  `tests/oracle/gen_fixture.py` in a disposable torch venv — Python/torch never a
  dependency). Result: **argmax exact at all 48 positions; last-row maxrel
  1.05e-6** (fp32-rounding scale); gate frozen at **maxrel ≤ 1e-5** + exact
  argmax + NaN-free. `make fidelity`.

Suite **129**; lint/fmt clean. Released: **0.1.0 · 0.2.0 · 0.3.0 · 0.4.0 · 0.5.0 · 1.0.0 · 1.1.0 · 1.1.1**.

## Toolchain

Cyrius pin **6.3.31** (`cyrius.cyml`; bumped 6.3.27→6.3.31 at 0.2.0 to pick up
the re-folded ganita `f64_tanh` fix). Deps wired: `sigil` + `tula` + `rosnet` +
`rupantara` (+ stdlib bayan/math/ganita).

## Build artifacts

- `src/main.cyr` → `build/anukulana` (the reference binary; no distlib).
- CI + release workflows in `.github/workflows/`. `cyrius.lock` gitignored.
- `tests/fixtures/gpt2_oracle_v1.bin` (1.2 MB) — committed HF-oracle fixture
  (test data; regenerate only on format/sequence-set change).

## Cross-repo status

- **tula** — released 1.0.0 (format frozen). anukulana **M1 DONE** (consumed).
- **rupantara** — released 0.4.0 (forward + KV-cache decode, parity-proven).
  Consumed by the import path; **M2 DONE** on it.
- **rosnet 0.2.0 / sigil 3.9.9+** — consumed (tensors / signature verify).
- **akshara** — not yet wired (the oracle uses integer token patterns; a real
  tokenizer enters with the LoRA fine-tune data path if needed).

## Next

**M3 (LoRA) ✅ CLOSED + M4 (QLoRA/NF4) ✅ CORE COMPLETE — shipped in 0.4.0,
2026-07-04.** M3: `src/lora.cyr` (fwd/bwd/merge/xent/SGD/**Adam**, FD-gated
dA+dB entry-by-entry) + `gpt2-lora` head adapter — xent 10.79→0.0000, argmax
1/8→8/8, base bit-frozen (head-adapter scope accepted by the user; deeper
adapters would patch **attn11** if ever wanted — allowed except SIMD, which
cyrius delivers next arc). M4: `src/nf4.cyr` (NF4 codec + double-quant, 8-test
exactness gate) + `gpt2-qlora` — the whole 124M base at 4 bits (codes 62 MB),
adapter recovers the task 8/8 over it, codes bit-frozen; 4-bit drift at 124M
scale reported honestly. Findings: plain SGD diverges on real-GPT-2 features
(massive-activation outliers → Adam required); the NF4 table's largest gap is
on the NEGATIVE side. **The persistence bite shipped in 0.5.0** (signed NF4
checkpoint + adapter via tula, bit-identical round-trips, trust boundary
gated). **1.0.0 SHIPPED same day** — API frozen, fuzz gate added (2 audit fixes
in `st_open` folded in), benchmarks + audit + SECURITY.md landed. Post-1.0 =
maintenance + the additive lane. **The GGUF headline landed 2026-07-05** (see
Version above) — remaining additive lanes: quantized GGML payloads,
llama-architecture (TinyLlama-class) mapping, NF4 throughput (SIMD-gated).
See `roadmap.md`.
