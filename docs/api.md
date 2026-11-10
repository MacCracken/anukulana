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
| `inspect <file.tula> [--pk <key file>]` | open a sovereign tula checkpoint: list tensors + report signature status. *(1.4.0)* Prints the file's signed metadata, reads files of any size, and with `--pk` (a 32-byte public key, or a 64-byte seed\|\|pk whose halves agree) verifies the signature: exit 1 for a bad signature **or an unsigned file** |
| `version` | print the packed version int (`major*10000 + minor*100 + patch`) |
| `gpt2 <model.safetensors>` | import a real GPT-2-small checkpoint, run its forward, cross-check batch == KV-cache decode (bit-identical); the no-oracle validation |
| `gpt2-oracle <model.safetensors> <fixture.bin>` | the **HF-fidelity gate**: per-position argmax must equal HF's exactly, last-row maxrel ≤ 1e-5 vs the committed reference fixture |
| `gpt2-lora <model.safetensors>` | LoRA head-adapter fine-tune over the frozen base (Adam); gates adaptation 8/8 + base bit-frozen + adapter-off bit-identical |
| `gpt2-qlora <model.safetensors>` | QLoRA: NF4-quantize the whole base (tula codec + local double-quant), adapter recovers the task over the frozen 4-bit base |
| `gpt2-tula <model> <ckpt.tula> <adapter.tula> [--sk <operator.sk>]` | signed persistence round-trip: save/load NF4 checkpoint + adapter, everything bit-identical, tamper/wrong-key rejected. `--sk` *(1.1.1)*: sign with a real 64 B seed\|\|pk operator key file (ifran's `keys init` layout) instead of the ephemeral demo key — a control plane's `store add` then records `verified` |
| `gpt2-gguf <model.gguf>` *(1.1.0)* | import via the **GGUF door** (llama.cpp format), run the forward, cross-check batch == KV-cache decode (bit-identical) |
| `convert <model.{safetensors,gguf}> <out.tula> [--sk <operator.sk>]` *(1.5.0)* | write the model as a **signed tula file at its source precision** (F64/F32/F16/BF16, HF GPT-2 names and shapes; GGUF weights transposed back), with metadata and provenance, then reload it and require its packed params **bit-identical** to a direct import. Without `--sk` it signs with the demo key (integrity only). Safetensors heads come from `config.json`'s `n_head` beside the model, else 12 |
| `gpt2-load <model.tula> [--pk <key file>]` *(1.5.0)* | import a converted file (signature verified; without `--pk`, against the demo key) and run the batch == KV-cache decode check |
| `gpt2-cross <model.safetensors> <model.gguf>` *(1.1.0)* | the **cross-format gate**: the same checkpoint through both foreign parsers must produce bit-identical packed params AND logits |
| `gpt2-qgguf <reference> <quantized.gguf>` *(1.6.0)* | a **llama.cpp-quantized GPT-2** (Q4_0 / Q4_1 / Q5_0 / Q5_1 / Q8_0; *(1.6.1)* the K-quants, e.g. `Q4_K_M`) against the unquantized import of the same checkpoint (HF safetensors, heads from a `config.json` beside it, or an F32 / F16 GGUF). Gates: same config, at least one block-typed tensor, NaN-free, batch == decode bit-identical, weights closer to the reference than zero is (relative RMS error < 1). Reported: the tensor types, the params that differ bit for bit *(1.6.1)*, the weight error (max, relative RMS), the logit drift and the argmax agreement over 8 positions |

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
(widens F64/F32/F16/BF16 per dtype). *(1.3.0)* `st_read_f64_range(r, e, start, n,
dst)` → 0 | -1 (a flat element range, widened; -1 outside the tensor or for a
dtype that isn't a float weight) · `st_entry_nbytes(e)` (the payload's byte
span) · `ST_MAX_ELEMS()` (2^56, the element-count cap).

### GPT-2 mapping — `src/gpt2.cyr`
`anuk_gpt2_import(path, nh, T_run, cfg)` → params | 0 — one-shot: mmap → infer
config (heads passed in; NOT in safetensors) → pack onto rupantara's layout
(fused-QKV column split, **no transpose**). `anuk_gpt2_infer_cfg` /
`anuk_gpt2_pack` are the two halves. *(1.2.1)* The inferred config, and again the
config with `T_run` applied, must pass rupantara's `ru_cfg_check`, or import
returns 0 and `anuk_gpt2_infer_cfg` returns -1. *(1.5.1)* `T_run = 0` keeps the
file's own context (`wpe`'s rows, 1024 for GPT-2): one import then serves every run
length through rupantara's `ru_model_fwd_n(_s)` (rupantara 0.6), so nothing is
repacked per length, and its rows are bit-identical to a `T_run = n` import's
`ru_model_fwd`. *(1.2.2)* Every tensor must have
exactly HF GPT-2's shape (`wte` [V,C], `wpe` [≥T,C], `c_attn.weight` [C,3C], …),
not just its element count; `anuk_gpt2_pack` returns -2 otherwise.
*(1.3.0)* `anuk_decode_check(cfg, params, tokens, Lb)` → the number of differing
logits | a negative `RU_ERR_*` — the batch forward over `T` tokens into `Lb`
(`T`×`V`), then the KV-cache decode token by token, compared bit for bit;
allocation-free per token (the `gpt2` / `gpt2-gguf` gate) · *(1.5.1)*
`anuk_decode_check_n(cfg, params, tokens, n, Lb)` — the same over the first `n`
positions (`1 <= n <= T`; `Lb` is `n`×`V`), so a full-context import checks a short
run: the batch is `ru_model_fwd_n_s`; `RU_ERR_POS` for `n > T`, `RU_ERR_ARG` for
`n < 1`. `anuk_decode_check` is its `n = T` case ·
`anuk_argmax_matches(logits, targets, T, V)` → how many of the `T` rows have
their argmax at `targets[t]`.

### Foreign import — `src/gguf.cyr` (untrusted input; added 1.1.0)
`gg_open(buf, len)` → reader | 0 (GGUF v2/v3 — typed-KV walk with structural
skip of unread values, ne-order tensor infos, `general.alignment`, per-tensor
extent validation; wrap-safe bounds throughout; fuzz-gated in
`tests/tcyr/fuzz.tcyr`) · `gg_open_mmap(path)` · accessors `gg_count` /
`gg_entry` / `gg_entry_{name,name_len,ndim,dim,gtype,nelems,data}` / `gg_find`
· KV lookups `gg_kv_int(r, key, found)` / `gg_kv_str(r, key, out_len)` ·
`gg_read_f64(r, e, dst)` (widens F32/F16; see 1.6.0 for the block types).
*(1.2.2)* Element counts are checked at every multiply; KV integers are read at
their own width and i8/i16/i32 sign-extended; `gg_entry_dim` is 0 past ndim.
*(1.3.0)* `gg_read_f64_range(r, e, start, n, dst)` → n | -1 (a flat element
range, widened) · `GG_MAX_ELEMS()` (2^29, the element-count cap).
*(1.6.0)* **llama.cpp's legacy block types** open and read: Q4_0, Q4_1, Q5_0, Q5_1
and Q8_0 (32 weights per block; ids `GG_T_Q4_0()` 2, `GG_T_Q4_1()` 3,
`GG_T_Q5_0()` 6, `GG_T_Q5_1()` 7, `GG_T_Q8_0()` 8, with `GG_T_F32()` 0 and
`GG_T_F16()` 1). `gg_read_f64` / `gg_read_f64_range` give **exactly ggml's own f32
dequantization**, widened (any range, on or off block boundaries). `gg_open` also
requires a block tensor's `ne0` to be whole blocks, and still rejects every other
type id (the K-quants among them). `gg_entry_nbytes(e)` (the payload's bytes) ·
`gg_type_name(t)` (`"Q8_0"`, …, `"?"`) · `gg_type_is_quant(t)`. Held by
`tests/fixtures/gguf_qblocks_v1.gguf` (gguf-py's `dequantize` as the oracle) and
fuzz rounds against a guard page.
*(1.6.1)* **The K-quants** open and read the same way: Q2_K, Q3_K, Q4_K, Q5_K and
Q6_K (256-weight superblocks; ids `GG_T_Q2_K()` 10 … `GG_T_Q6_K()` 14), so
llama.cpp's standard mixes (`Q2_K`, `Q3_K_M`, `Q4_K_M`, `Q5_K_M`, `Q6_K`) import. A
K-quant tensor's `ne0` must be whole superblocks. Still rejected: Q8_K (15, not a
storage type), the IQ / TQ types, MXFP4 and BF16. Held by
`tests/fixtures/gguf_kblocks_v1.gguf` (gguf-py's `dequantize`) and, on real files,
by llama.cpp's own dequantization (`tests/oracle/gen_kquants.sh --oracle`).

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
*(1.5.1)* `T_run = 0` keeps the file's own context (`position_embd`'s rows), as for
the safetensors door; `anuk_ggpt2_infer_cfg` reads it the same way. *(1.6.0)* Any
tensor may be in a block type (llama.cpp quantizes `token_embd` and the four block
weights); the import holds ggml's dequantized values as f64.
`anuk_weight_drift(p, q, n, out)` (in `src/gpt2.cyr`) → 0 — `out[0]` the max
`|p - q|`, `out[1]` the relative RMS error `sqrt(Σ(p-q)² / Σp²)` (both f64),
`out[2]` the NaN count in `q`, which both sums skip; `gpt2-qgguf`'s measure.

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

### Convert — `src/convert.cyr` (added 1.5.0)
`anuk_convert_safetensors(src_path, nh, out_path, sk)` / `anuk_convert_gguf(src_path,
out_path, sk)` → 0 | -1 — write a signed tula file holding HF GPT-2's tensor set
under its HF names and shapes, each in its source dtype (safetensors payloads
copied byte for byte; GGUF's `[out, in]` weights transposed back exactly, so both
doors give byte-identical tensors), the full context, a `"cfg"` F64 [8] tensor and
metadata (`anukulana.kind = model`, `anukulana.layout = hf-gpt2`, `.config`,
`.source.*`, and `hf.config` from a `config.json` beside the source). Same inputs →
byte-identical files. -1 for a source the importer would refuse or a failed write.
*(1.6.0)* A block-typed GGUF tensor is written as **F32 holding exactly ggml's
dequantized values** (each is an f32), so the file loads to what importing the
GGUF gives; the source's block types are recorded as `anukulana.source.quant`
(`"Q4_0"`, or a comma-separated list). Keeping the codes packed is later 1.6.x.
`anuk_tula_import(path, pk, T_run, cfg)` → params | 0 — open a converted file
(strict validation, Ed25519 under `pk` required, kind/layout checked, `T_run` ≤
the file's context; *(1.5.1)* `T_run = 0` is the file's context) and pack it
through the same mapping as the safetensors door, so it lands bit-identical to the
direct import. `anuk_hf_n_head(text, fallback)`
(`n_head` from a `config.json` text). The pack's tensor source is shared:
`GSRC_ST()` / `GSRC_TULA()` and `anuk_tula_read_f64_range(r, e, start, n, dst)` (in
`src/gpt2.cyr`). Loading verifies the whole file's signature every time: about 27 s
for GPT-2 small (~500 MB) at sigil's current SHA-512 speed.

### Inspection — `src/inspect.cyr`
`anuk_inspect(path)` → tensor count | -1 · `anuk_enumerate(r)` · `anuk_verify(r,
pk)`. *(1.4.0)* `anuk_inspect_pk(path, pk)` → tensor count | -1 (missing or
malformed) | -2 (with `pk`: unsigned or a bad signature) — reads any size through
a private mapping · `anuk_pk_load(path)` → 32-byte public key | 0 ·
`anuk_print_meta(r)` → the metadata pair count. tula's own tables
(`__tula.meta__`, `__tula.names__`) are not counted or listed as tensors.

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

*(1.4.0)* `anuk_nf4_save_src(path, cfg, params, sk, src_path)` /
`anuk_adapter_save_src(path, A, B, C, r, V, s, sk, base_path)` — the savers, also
recording the input file (`src_path`: the model; `base_path`: the checkpoint the
adapter was trained over; 0 for none). Both savers now use tula's checked adds
and its streaming, crash-safe signed writer (no 2 GiB cap; strictly valid output)
and write **signed metadata** (tula 1.6, ADR 0008), derived from their inputs
only, so the same inputs give byte-identical files:

| Key | In | Value |
|---|---|---|
| `anukulana.kind` | both | `nf4-checkpoint` / `lora-adapter` |
| `anukulana.version` | both | the writer's version, `major.minor.patch` |
| `anukulana.layout` | checkpoint | `rupantara-gpt2` (the packed parameter layout) |
| `anukulana.config` | checkpoint | the cfg as JSON (`V`, `C`, `T`, `nh`, `nkv`, `NL`, `F`, `attn_bias`) |
| `anukulana.nf4` | checkpoint | the NF4 parameters as JSON (block 64, superblock 256) |
| `anukulana.adapter` | adapter | `{"C":…,"r":…,"V":…,"target":"lm_head"}` |
| `anukulana.source.{name,bytes,format,sha256}` | checkpoint (`_src`) | the model file: basename, size, `safetensors` / `gguf` / `tula` / `unknown`, SHA-256 hex |
| `anukulana.base.{name,bytes,format,sha256}` | adapter (`_src`) | the base checkpoint, likewise |
| `anukulana.source.quant` *(1.6.0)* | converted model | the source GGUF's block types, dequantized to F32 (`Q8_0`, or a list such as `Q4_0,Q8_0`); absent for an unquantized source |

The key names are part of the file layout from 1.4.0; readers must tolerate keys
they don't know. The loaders still read the `"cfg"` tensor, not the metadata.

### Demo helpers — `src/lora_demo.cyr`
`anuk_frozen_features(cfg, params, tokens, T)` → f(T,C) — the frozen forward's
final-LN features, composed from rupantara's public ops (once-per-run).

## Out of freeze

- **The 1.2.2 additions, settled at 1.3.0.** Frozen above: `st_read_f64_range`,
  `st_entry_nbytes`, `ST_MAX_ELEMS`, `gg_read_f64_range`, `GG_MAX_ELEMS`,
  `anuk_decode_check`, `anuk_argmax_matches`. Made internal (renamed with a `_`):
  the demos' fixed token pattern (`_anuk_demo_tokens` / `_anuk_demo_targets`) and
  their shared head adapter (`_anuk_head_adapter_*`), which carries the demo
  knobs below (seed 20260704, init std 0.02).
- Everything `_`-prefixed (wideners, LE readers, print helpers, fuzz LCG).
- The demo training hyperparameters (steps/lr/r/seed inside `gpt2-lora` /
  `gpt2-qlora` / `gpt2-tula`) — the *gates* are frozen, the knobs are not.
- Checkpoint/adapter tensor **names** are frozen (`"cfg"`, `"base.nf4"`,
  `"base.nf4.scale.q8"`, `"base.nf4.scale.sup"`, `"lora.A"/"lora.B"/"lora.meta"`);
  additive tensors may appear in 1.x (readers must tolerate extras).
- **GGUF import** landed as **1.1.0** (2026-07-05): `gg_*` +
  `anuk_ggpt2_*` + the `gpt2-gguf` / `gpt2-cross` commands above are now part
  of the frozen surface.
