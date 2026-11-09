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
| `gpt2-tula <model> <ckpt.tula> <adapter.tula> [--sk <operator.sk>]` | signed persistence round-trip: save/load NF4 checkpoint + adapter, everything bit-identical, tamper/wrong-key rejected. `--sk` *(1.1.1)*: sign with a real 64 B seed\|\|pk operator key file (ifran's `keys init` layout) instead of the ephemeral demo key — a control plane's `store add` then records `verified` |
| `gpt2-gguf <model.gguf>` *(1.1.0)* | import via the **GGUF door** (llama.cpp format), run the forward, cross-check batch == KV-cache decode (bit-identical) |
| `gpt2-cross <model.safetensors> <model.gguf>` *(1.1.0)* | the **cross-format gate**: the same checkpoint through both foreign parsers must produce bit-identical packed params AND logits |

Exit code 0 = all gates PASS; 1 = a gate failed or an argument is missing (each
command prints which); 2 = an unknown command or option *(1.2.2; an unknown
command used to print the usage and exit 0)*. Results go to stdout, errors to
stderr *(1.2.2)*. `help` / `--help` / `-h` print the usage. `make fidelity` wraps
`gpt2-oracle` with the committed fixture.

## Module surface (frozen)

### Foreign import — `src/safetensors.cyr` (untrusted input)
`st_open(buf, len)` → reader | 0 (**the untrusted-input gate** — bounds-checked
header/offsets, malformed → clean reject; *(1.2.2)* integer non-negative dims
whose product can't wrap, and a fixed-width tensor's payload exactly shape ×
element size; fuzz-gated in `tests/tcyr/fuzz.tcyr`) · `st_read_file(path,
maxlen)` · `st_open_mmap(path)` (zero-copy, for >256 MB files) · accessors
`st_count` / `st_entry` / `st_entry_{name,name_len,dtype,ndim,dim,nelems,data}` /
`st_find` (`st_entry_dim` is 0 past ndim, 1.2.2) · `st_read_f64(r, e, dst)`
(widens F64/F32/F16/BF16 per dtype).

### GPT-2 mapping — `src/gpt2.cyr`
`anuk_gpt2_import(path, nh, T_run, cfg)` → params | 0 — one-shot: mmap → infer
config (heads passed in; NOT in safetensors) → pack onto rupantara's layout
(fused-QKV column split, **no transpose**). `anuk_gpt2_infer_cfg` /
`anuk_gpt2_pack` are the two halves. *(1.2.1)* The inferred config, and again the
config with `T_run` applied, must pass rupantara's `ru_cfg_check`, or import
returns 0 and `anuk_gpt2_infer_cfg` returns -1. *(1.2.2)* Every tensor must have
exactly HF GPT-2's shape (`wte` [V,C], `wpe` [≥T,C], `c_attn.weight` [C,3C], …),
not just its element count; `anuk_gpt2_pack` returns -2 otherwise.

### Foreign import — `src/gguf.cyr` (untrusted input; added 1.1.0)
`gg_open(buf, len)` → reader | 0 (GGUF v2/v3 — typed-KV walk with structural
skip of unread values, ne-order tensor infos, `general.alignment`, per-tensor
extent validation; wrap-safe bounds throughout; fuzz-gated in
`tests/tcyr/fuzz.tcyr`) · `gg_open_mmap(path)` · accessors `gg_count` /
`gg_entry` / `gg_entry_{name,name_len,ndim,dim,gtype,nelems,data}` / `gg_find`
· KV lookups `gg_kv_int(r, key, found)` / `gg_kv_str(r, key, out_len)` ·
`gg_read_f64(r, e, dst)` (widens F32/F16; quantized GGML block types reject).
*(1.2.2)* Element counts are checked at every multiply; KV integers are read at
their own width and i8/i16/i32 sign-extended; `gg_entry_dim` is 0 past ndim.

### GPT-2 mapping (GGUF) — `src/gpt2_gguf.cyr` (added 1.1.0)
`anuk_ggpt2_import(path, T_run, cfg)` → params | 0 — one-shot: mmap → infer
config **from KV metadata** (`general.architecture` must be `gpt2`; heads come
from `gpt2.attention.head_count` — unlike safetensors, GGUF carries them) →
pack onto rupantara's layout (ggml `[out, in]` **transposed back** to
`[in, out]`, fused-`attn_qkv` split by out-range). `anuk_ggpt2_infer_cfg` /
`anuk_ggpt2_pack` are the two halves. *(1.2.1)* `anuk_ggpt2_infer_cfg` returns -1
for a config `ru_cfg_check` rejects (e.g. `head_count = 0`, or one not dividing
`embedding_length`). *(1.2.2)* Every tensor must have exactly its expected
`ne` (an `attn_qkv` with more or fewer than 3C output rows is rejected).

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
key / tamper**, and *(1.2.1)* on a `cfg` tensor `ru_cfg_check` rejects, and
*(1.2.2)* on a file tula's strict validator rejects or any tensor not exactly
its layout's dtype and shape. The adapter loader applies the same checks and
returns -1; its meta rank must equal the caller's r.
`anuk_adapter_save(path, A, B, C, r, V, s, sk)` /
`anuk_adapter_load(path, pk, A_out, B_out, C, r, V, out_s)`. Round-trips are
bit-identical by contract (quantized data is discrete). `anuk_sk_load(path)`
*(1.1.1)* — load a 64 B seed||pk secret-key file (sigil's `ed25519_keypair` sk
layout = ifran's `operator.sk`); pk is the trailing 32 bytes (`sk + 32`);
returns 0 on an absent file, *(1.2.2)* on any file that isn't exactly 64 bytes,
and on one whose pk half isn't the public key of its seed half.

### Demo helpers — `src/lora_demo.cyr`
`anuk_frozen_features(cfg, params, tokens, T)` → f(T,C) — the frozen forward's
final-LN features, composed from rupantara's public ops (once-per-run).

## Out of freeze

- **Added in 1.2.2, out of freeze until the next minor** (a patch adds no frozen
  surface, per `STABILITY.md`): `st_read_f64_range(r, e, start, n, dst)` /
  `gg_read_f64_range(r, e, start, n, dst)` (a flat element range, widened) ·
  `st_entry_nbytes(e)` · `ST_MAX_ELEMS()` / `GG_MAX_ELEMS()` ·
  `anuk_decode_check(cfg, params, tokens, Lb)` → logit diffs | `RU_ERR_*` (batch
  vs KV-cache decode, allocation-free per token) · `anuk_demo_tokens(T, V)` /
  `anuk_demo_targets(tokens, T)` / `anuk_argmax_matches(logits, targets, T, V)` ·
  `anuk_head_adapter_new / _a / _b / _fwd / _fwd_with / _train` (the demos' shared
  LoRA head adapter).
- Everything `_`-prefixed (wideners, LE readers, print helpers, fuzz LCG).
- The demo training hyperparameters (steps/lr/r/seed inside `gpt2-lora` /
  `gpt2-qlora` / `gpt2-tula`) — the *gates* are frozen, the knobs are not.
- Checkpoint/adapter tensor **names** are frozen (`"cfg"`, `"base.nf4"`,
  `"base.nf4.scale.q8"`, `"base.nf4.scale.sup"`, `"lora.A"/"lora.B"/"lora.meta"`);
  additive tensors may appear in 1.x (readers must tolerate extras).
- **GGUF import** landed as **1.1.0** (2026-07-05): `gg_*` +
  `anuk_ggpt2_*` + the `gpt2-gguf` / `gpt2-cross` commands above are now part
  of the frozen surface.
