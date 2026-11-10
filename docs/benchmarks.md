# anukulana — Benchmarks

> Box (both captures): AMD Ryzen 7 5800H (Zen 3), x86_64 Linux. Model: HF GPT-2-small (124M,
> 548 MB fp32 safetensors at `~/models/gpt2/`; since 1.3.0 pinned to revision `607a30d7`, sha256
> `248dfc39…`). Single-threaded CPU f64 (rosnet/rupantara). End-to-end numbers are wall-clock via
> `time`, one representative run each — re-capture on toolchain or hardware change.

## Import hot paths — `make bench` (1.2.2, 2026-11-09)

`tests/anukulana.bcyr` times the import's inner loops on synthetic, f32-exact data, so it needs no
checkpoint. Same host and session, cyrius 6.7.18, median of 3 runs. 1.2.2's outputs are bit-identical to
1.2.1's (held by `tests/tcyr/safetensors.tcyr`'s widener-equivalence test and the round-trip suites).

| Bench | 1.2.1 | 1.2.2 | |
|---|---|---|---|
| `st_read_f64 F32 n=1M` | 12.862 ms | 5.598 ms | 2.30× |
| `st_read_f64 F16 n=1M` | 11.185 ms | 8.199 ms | 1.36× |
| `gg_read_f64 F32 n=1M` | 8.208 ms | 5.499 ms | 1.49× |
| `anuk_gpt2_pack F32 V=2048 C=128 T=64 NL=4` (1.06M params) | 13.708 ms | 5.711 ms | 2.40× |
| `anuk_ggpt2_pack F32 V=2048 C=128 T=64 NL=4` | 14.325 ms | 8.033 ms | 1.78× |
| `nf4_dq_pack nb=64k` (unchanged code) | 0.417 ms | 0.410 ms | — |
| `nf4_dq_unpack nb=64k` (unchanged code) | 0.264 ms | 0.273 ms | — |

**1.6.0's block decoders** (same host, cyrius 6.7.18, one run): `gg_read_f64` over 1M weights takes
**3.79 ms for Q8_0**, **3.31 ms for Q4_0** and **6.40 ms for Q4_1**, against 5.93 ms for F32 in the same
run. Q8_0 and Q4_0 read fewer bytes than F32; Q4_1 (like Q5_1, not benched) pays for the f32 rounding of `q * d + m`.
**The K-quants** (same host, one run): **6.96 ms for Q4_K** and **5.44 ms for Q6_K** per 1M weights
(F32 6.01 ms in that run). Q6_K took 9.64 ms until its 16 `d * scale` products were computed once per
superblock instead of four times per weight position (bit-identical).

What moved: one `load32` per f32 instead of four byte loads; bulk widen loops that rebias normal numbers
inline; the safetensors fused QKV split straight into place and `wpe` read to T rows; GGUF transposes that
widen each element once (QKV was widened three times). The end-to-end gain on the real checkpoint is in the
table below (1.3.0).

## End-to-end CLI commands — 1.0 vs 1.3.0

1.0: 2026-07-04, cycc 6.4.2 (pin 6.3.31). 1.3.0: 2026-11-09, cyrius 6.7.18 (sigil 3.13.15, tula 1.6.1,
rosnet 1.4.1, rupantara 0.5.3). Every gate passed in both captures.

| Command | 1.0 | 1.3.0 | What it covers |
|---|---|---|---|
| `gpt2` | 3.9 s | **2.19 s** | mmap + parse + fp32→f64 widen + pack (123.6M params) + batch fwd (T=8) + KV-decode cross-check |
| `gpt2-oracle` | 7.2 s | **4.20 s** | import (T=16) + 3 × T=16 forwards + 3 × 50257-logit compares vs the fixture |
| `gpt2-gguf` | — | **2.47 s** | the `gpt2` check through the GGUF door (GGUF from `tests/oracle/gen_gguf.py`) |
| `gpt2-cross` | — | **3.24 s** | both imports + packed-param and logit bit-compare (0 diffs of 123,659,520 / 402,056) |
| `gpt2-lora` | 13.3 s | **26.60 s** | import + frozen forward (features once) + **800 Adam steps** of head-adapter training + gates |
| `gpt2-qlora` | 53.5 s | **35.22 s** | import + NF4-quantize all 123.6M params + double-quant + dequant + 2 full forwards + 800 adapter steps |
| `gpt2-tula` | 79.5 s | **50.15 s** | the qlora pipeline + signed 63.8 MB checkpoint write/read/verify + adapter write/read/verify + bit-compares |
| `convert` *(1.5.0)* | — | **86.8 s** | import + write the 497.8 MB F32 file (source SHA-256 1.7 s, Ed25519 sign ~54 s) + reload (verify ~27 s) + bit-compare |
| `gpt2-load` *(1.5.0)* | — | **29.3 s** | verify the converted file's signature (~27 s) + pack + the batch == decode check |
| `gpt2-gguf` Q8_0 / Q4_0 *(1.6.0)* | — | **2.66 s / 2.13 s** | the `gpt2-gguf` check on gguf-py-quantized files (134.9 MB / 73.1 MB) |
| `gpt2-qgguf` *(1.6.0)* | — | **9.2–10.3 s** | both imports, the weight drift over 124.4M params, the batch == decode check, 8 reference positions |
| `convert` Q4_0 *(1.6.0)* | — | **79.0 s** | dequantize to exact F32 + sign the 497.8 MB file + reload (verify) + bit-compare |
| `gpt2-gguf` Q4_K_M *(1.6.1)* | — | **3.16 s** | the `gpt2-gguf` check on llama.cpp's own Q4_K_M file (89.5 MB) |
| `convert` Q4_K_M *(1.6.1)* | — | **91.9 s** | as for Q4_0; `gpt2-load` of the result 30.5 s |
| `convert` Q8_0 *(1.6.1)* | — | **25.4 s** | kept packed: a 134.9 MB file (not 497.8 MB), so signing is about a quarter; `gpt2-load` of it **10.6 s** |

Fidelity at 1.3.0: argmax exact at all 48 positions, worst last-row maxrel **1.049e-6** (1.0: 1.05e-6), so
the GELU `tanh` change at cyrius 6.6.13 (up to 2 ulp) did not move the gate.

## Derived observations

- **Import got faster:** `anuk_gpt2_import` takes **0.75 s** on the real checkpoint and `anuk_ggpt2_import`
  **1.05 s** (about 3.5 s at 1.0). Measured on the same box against the unmodified 1.2.1 code (1.72 s and
  1.77 s), 1.2.2's widen and pack changes are 2.3× and 1.7× on real weights, in line with the synthetic
  predictions above (2.40×, 1.78×).
- **NF4 quantization is about 4.7 s** for the full model at 1.3.0 (tula 1.6.1's `tula_nf4_pack`: 16M
  params in 0.64 s; unpack 0.07 s), down from about 25 s at 1.0. That is why `gpt2-qlora` and `gpt2-tula`
  got faster despite the training loop below.
- **Head-adapter training is the slow part now: about 30 ms per step, 24 s for 800 steps.** Measured per
  step at the real dims (T=8, C=768, V=50257, r=8): `ru_softmax_fwd` over the 402k logits 10.0 ms
  (rupantara; 58 % of it is the cyrius `f64_exp` builtin, x87 on x86_64, about 14.5 ns each), `lora_adam` on B (402k params) 9.1 ms,
  `lora_bwd` 5.4 ms, `lora_fwd` 4.0 ms, `lora_xent_bwd` 1.4 ms. The unmodified 1.2.1 code takes 27.3 s for
  `gpt2-lora` on the same box, so 1.2.2's refactor didn't cause it; it came with the toolchain and
  dependency moves since 1.0. **Correction:** this file's 1.0 note said "800 Adam steps cost ~2 s"; its own
  table implies about 9 s (13.3 s total minus about 3.9 s of import and forward), so per step the loop is
  about 2.6× slower than at 1.0, not 12×. The roadmap tracks it (1.x.x).
- Artifact sizes: **63.8 MB** signed NF4 checkpoint (codes + INT8 scale codes +
  F64 superblock maxes + cfg) vs 548 MB foreign fp32 file vs 989 MB f64 in
  memory; adapter **3.3 MB** (A 768×8 + B 8×50257, f64).

## Honest framing

These are correctness-first reference paths on the sovereign CPU substrate —
no BLAS, no threads, no SIMD beyond rosnet's 4-lane f64. The comparison points
that matter are the *gates* (HF-exact fidelity, bit-identical round-trips),
not throughput; throughput belongs to the rosnet/mabda optimization lanes.
