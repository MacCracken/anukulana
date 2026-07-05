# anukulana — Benchmarks

> v1.0 capture (2026-07-04). Box: AMD Ryzen 7 5800H (Zen 3), x86_64 Linux,
> cycc 6.4.2 (pin 6.3.31). Model: HF GPT-2-small (124M, 548 MB fp32
> safetensors, staged at `~/models/gpt2/`). Single-threaded CPU f64
> (rosnet/rupantara). Wall-clock via `time`, one representative run each —
> re-capture on toolchain or hardware change.

## The v1.0 numbers (end-to-end CLI commands)

| Command | Wall | What it covers |
|---|---|---|
| `gpt2` | **3.9 s** | mmap + parse + fp32→f64 widen + pack (123.6M params) + batch fwd (T=8) + KV-decode cross-check |
| `gpt2-oracle` | **7.2 s** | import + 3 × T=16 forwards + 3 × 50257-logit compares vs the fixture |
| `gpt2-lora` | **13.3 s** | import + frozen forward (features once) + **800 Adam steps** of head-adapter training + gates |
| `gpt2-qlora` | **53.5 s** | import + NF4-quantize all 123.6M params + double-quant + dequant + 2 full forwards + 800 adapter steps |
| `gpt2-tula` | **79.5 s** | the qlora pipeline + signed 63.8 MB checkpoint write/read/verify + adapter write/read/verify + bit-compares |

## Derived observations

- **Import is ~3.5 s** of every command (dominated by the 123.6M-element
  fp32→f64 widen + pack); the forward at T=8 is ~0.4 s/pass (consistent with
  rosnet's `linear_fwd` numbers — see rosnet `docs/benchmarks.md`; the
  50257-vocab head is the bulk).
- **Head-adapter training is cheap by construction** — features are computed
  once, so 800 Adam steps cost ~2 s (each step is head-sized: r=8 adapter over
  T=8×C=768 features → V=50257 logits).
- **NF4 quantization of the full model is ~25 s** (123.6M × nearest-of-16
  codebook scan, scalar) — a linear scan per weight; acceptable for a
  quantize-once artifact, an obvious post-1.0 optimization target if it ever
  runs hot (branchless compare tree, or SIMD when cyrius ships it).
- Artifact sizes: **63.8 MB** signed NF4 checkpoint (codes + INT8 scale codes +
  F64 superblock maxes + cfg) vs 548 MB foreign fp32 file vs 989 MB f64 in
  memory; adapter **3.3 MB** (A 768×8 + B 8×50257, f64).

## Honest framing

These are correctness-first reference paths on the sovereign CPU substrate —
no BLAS, no threads, no SIMD beyond rosnet's 4-lane f64. The comparison points
that matter are the *gates* (HF-exact fidelity, bit-identical round-trips),
not throughput; throughput belongs to the rosnet/mabda optimization lanes.
