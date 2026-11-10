# anukulana — Current State

> **Last refresh**: 2026-11-09 (1.5.0) | **Cadence**: every release.
> `CLAUDE.md` is preferences/process; this file is volatile state.

## Version

**1.5.0 — 2026-11-09 (`convert` at source precision).** `convert` writes a foreign GPT-2 as a signed tula
file in HF GPT-2's names and shapes at its source dtype (GGUF weights transposed back), with metadata and
provenance, and self-checks: the reload is bit-identical to a direct import. `gpt2-load` runs from the
file. On the real checkpoint both doors reload bit-identical and their files hold byte-identical tensors
(148, 497.8 MB). `convert` ~86 s and `gpt2-load` ~29 s, nearly all Ed25519 over sigil's 18.4 MB/s
SHA-512 (upstream). Suite **286**.

**1.4.0 — 2026-11-09 (the tula 1.2–1.6 surface).** Every checkpoint and adapter carries signed metadata
(`anukulana.*`: kind, version, layout, config, and with the `_src` savers the source model's or base
checkpoint's SHA-256); same inputs → byte-identical files. `inspect --pk` verifies signatures (an unsigned
file fails), prints the metadata and reads any size. Saves use tula's checked adds and its streaming,
crash-safe signed writer; loaders look up by full name. Suite **257**.

**1.3.0 — 2026-11-09 (re-proven on real weights).** All seven real-checkpoint commands pass on HF GPT-2
small (now pinned by revision and sha256) at cyrius 6.7.18: fidelity argmax exact 48/48, worst maxrel
1.049e-6; `gpt2-cross` bit-identical; LoRA/QLoRA 8/8; the signed NF4 round trip bit-identical. Real-weights
import is 2.3× (safetensors) and 1.7× (GGUF) faster than 1.2.1, measured. New CI: `realweights.yml`
(manual), `bounds`, `aarch64`. The 1.2.2 helpers are frozen or made internal. `gpt2-lora` is slower than
at 1.0 (26.6 s; training steps cost about 30 ms, upstream math), tracked in the roadmap.

**1.2.2 — 2026-11-09 (the P(-1) hardening, optimization and repair sweep).**
[`docs/audit/2026-11-09-audit.md`](../audit/2026-11-09-audit.md): two HIGH
hostile-file crashes fixed (a safetensors shape never compared with its payload;
a GGUF weight overflowing a heap scratch), six MEDIUM (GGUF dim wrap and KV
width, unchecked tensors in signed files, count-not-shape mapping checks, the
operator-key file, the per-token decode allocation), LOW hygiene, CI hardening.
Import hot paths 1.4–2.4× faster, bit-identical. Suite **219** (was 139), green
plain, `--bounds` and `--aarch64`; 15/15 mutants killed.

**1.1.2 → 1.2.1 (2026-08-18 → 2026-11-09): toolchain and dependency realigns.**
6.3.31 → 6.5.27 → 6.6.2 → 6.6.20 → 6.7.9 (git-first deps) → 6.7.18, each with
its dependency set; 1.2.1 added rupantara's `ru_cfg_check` at every config built
from a file (a `head_count = 0` GGUF crashed with SIGFPE through 1.2.0). See the
CHANGELOG for each step.

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

Suite **219** (1.2.2); lint/fmt/vet/doc clean. Every version since 0.1.0 is in the CHANGELOG.

## Toolchain

Cyrius pin and dependency tags: see `cyrius.cyml` (1.2.2: cyrius 6.7.18 with sigil
3.13.15, tula 1.6.1, rosnet 1.4.1, rupantara 0.5.3; tyche 1.2.2 transitively).
Since 6.7.6 every build resolves the tags (git first); the `path = "../x"` lines
are dev overrides used only under `CYRIUS_LOCAL=1`. The history of each pin move,
including the 6.5.27 bump that took the suite from 0/9 to 9/9, is in the
CHANGELOG.

## Build artifacts

- `src/main.cyr` → `build/anukulana` (the reference binary; no distlib).
- CI + release workflows in `.github/workflows/`. `cyrius.lock` gitignored.
- `tests/fixtures/gpt2_oracle_v1.bin` (1.2 MB) — committed HF-oracle fixture
  (test data; regenerate only on format/sequence-set change).

## Cross-repo status

- **tula 1.6.1** (format v1 frozen) — anukulana **M1 DONE** (consumed); 1.2.2 uses
  its strict validator on every signed file it reads.
- **rupantara 0.5.3** (forward + KV-cache decode, validated entries) — consumed by
  the import path; **M2 DONE** on it. 1.2.2 decodes on its allocation-free `_s`
  entries, closing the cross-repo item its 2026-11-09 audit filed.
- **rosnet 1.4.1 / sigil 3.13.15** — consumed (tensors / Ed25519).
- **akshara** — not yet wired (the oracle uses integer token patterns; a real
  tokenizer enters with the LoRA fine-tune data path if needed).

## Next

rupantara 0.6–0.7 (1.6.x, gated on rupantara), quantized GGUF payloads (1.7.x) and the llama architecture
(1.8.x, gated on rupantara). The 1.x.x list holds the digest-pinned load (the maintainer's call) and
sigil's SHA-512 speed (upstream). See [`roadmap.md`](roadmap.md).
