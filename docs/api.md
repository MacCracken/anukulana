# anukulana — Public API (1.x FROZEN)

> **Frozen at v1.0.0 (2026-07-04).** anukulana is a **reference binary** (like
> attn11 / tarka / prajna) — the primary public surface is the **CLI**; the
> module functions below are frozen for in-repo/test consumption and for any
> future consumer that links the sources. Additions land as 1.x minors
> (additive only). Symbols prefixed `_` are internal and out-of-freeze. See
> [`STABILITY.md`](../STABILITY.md).

## The CLI (the primary surface)

| Command | Contract |
|---|---|
| `inspect <file.tula>` | open a sovereign tula checkpoint: list tensors + report signature status |
| `version` | print the packed version int (`major*10000 + minor*100 + patch`) |
| `gpt2 <model.safetensors>` | import a real GPT-2-small checkpoint, run its forward, cross-check batch == KV-cache decode (bit-identical); the no-oracle validation |
| `gpt2-oracle <model.safetensors> <fixture.bin>` | the **HF-fidelity gate**: per-position argmax must equal HF's exactly, last-row maxrel ≤ 1e-5 vs the committed reference fixture |
| `gpt2-lora <model.safetensors>` | LoRA head-adapter fine-tune over the frozen base (Adam); gates adaptation 8/8 + base bit-frozen + adapter-off bit-identical |
| `gpt2-qlora <model.safetensors>` | QLoRA: NF4-quantize the whole base (tula codec + local double-quant), adapter recovers the task over the frozen 4-bit base |
| `gpt2-tula <model> <ckpt.tula> <adapter.tula>` | signed persistence round-trip: save/load NF4 checkpoint + adapter, everything bit-identical, tamper/wrong-key rejected |

Exit code 0 = all gates PASS; non-0 = a gate failed (each command prints which).
`make fidelity` wraps `gpt2-oracle` with the committed fixture.

## Module surface (frozen)

### Foreign import — `src/safetensors.cyr` (untrusted input)
`st_open(buf, len)` → reader | 0 (**the untrusted-input gate** — bounds-checked
header/offsets, malformed → clean reject; fuzz-gated in `tests/tcyr/fuzz.tcyr`) ·
`st_read_file(path, maxlen)` · `st_open_mmap(path)` (zero-copy, for >256 MB
files) · accessors `st_count` / `st_entry` / `st_entry_{name,dtype,ndim,dim,
nelems,data_len,data}` / `st_find` · `st_read_f64(r, e, dst)` (widens
F64/F32/F16/BF16 per dtype).

### GPT-2 mapping — `src/gpt2.cyr`
`anuk_gpt2_import(path, nh, T_run, cfg)` → params | 0 — one-shot: mmap → infer
config (heads passed in; NOT in safetensors) → pack onto rupantara's layout
(fused-QKV column split, **no transpose**). `anuk_gpt2_infer_cfg` /
`anuk_gpt2_pack` are the two halves.

### Fidelity — `src/oracle.cyr`
`anuk_gpt2_oracle(model_path, fix_path)` → 0 | 1. Fixture format v1 documented
at the module head; gate = exact argmax every position + last-row maxrel ≤
`ORACLE_GATE_MAXREL()` (1e-5) + NaN-free.

### LoRA — `src/lora.cyr`
`lora_init(A, B, K, r, N, std)` (A gaussian via tyche, B zero) ·
`lora_fwd(x, A, B, u, t, y, M, K, r, N, s)` (`y += s·(x·A)·B`, caches u) ·
`lora_bwd(x, u, A, B, dy, dA, dB, dys, du, dxs, M, K, r, N, s)` (**two rosnet
`linear_bwd` passes** — dA/dB accumulate; FD-gated entry-by-entry) ·
`lora_merge(W, A, B, tmp, K, r, N, s)` (untied matrices only) ·
`lora_xent_loss(logits, probs, targets, M, V)` / `lora_xent_bwd(...)` ·
`lora_sgd(P, dP, n, lr)` · `lora_adam(P, dP, m, v, n, lr, step)` (bias-corrected;
**required on real-GPT-2 features** — flat-lr SGD diverges on the
massive-activation outlier dims).

### NF4 — `src/nf4.cyr` (delegates to tula's codec)
`NF4_BS()` (=`TULA_NF4_BLOCK`=64) · `NF4_SBS()` (=256) · `nf4_value` / `nf4_code`
/ `nf4_quant` / `nf4_dequant` (thin over `tula_nf4_*`) · **local layer:**
`nf4_dq_pack(scales, nblocks, q8, supers)` / `nf4_dq_unpack(...)` —
superblock-256 double-quantization of the per-block scales (symmetric-u8;
error ≤ 1/254 relative per scale).

### Persistence — `src/nf4_store.cyr` (trust boundary)
`anuk_nf4_save(path, cfg, params, sk)` / `anuk_nf4_load(path, pk, cfg_out)` —
signed NF4 checkpoint (`"cfg"` + `TULA_DT_NF4` codes + INT8 scale codes + F64
superblock maxes); **load verifies Ed25519 and returns 0 on unsigned / wrong
key / tamper**. `anuk_adapter_save(path, A, B, C, r, V, s, sk)` /
`anuk_adapter_load(path, pk, A_out, B_out, C, r, V, out_s)`. Round-trips are
bit-identical by contract (quantized data is discrete).

### Demo helpers — `src/lora_demo.cyr`
`anuk_frozen_features(cfg, params, tokens, T)` → f(T,C) — the frozen forward's
final-LN features, composed from rupantara's public ops (once-per-run).

## Out of freeze

- Everything `_`-prefixed (wideners, LE readers, print helpers, fuzz LCG).
- The demo training hyperparameters (steps/lr/r/seed inside `gpt2-lora` /
  `gpt2-qlora` / `gpt2-tula`) — the *gates* are frozen, the knobs are not.
- Checkpoint/adapter tensor **names** are frozen (`"cfg"`, `"base.nf4"`,
  `"base.nf4.scale.q8"`, `"base.nf4.scale.sup"`, `"lora.A"/"lora.B"/"lora.meta"`);
  additive tensors may appear in 1.x (readers must tolerate extras).
- **GGUF import** is the headline post-1.0 addition (a second foreign source —
  new parser module + mapping; additive).
