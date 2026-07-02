# Changelog

All notable changes to `anukulana` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); SemVer (pre-1.0 — surface still
moving, no API freeze until v1.0).

## [Unreleased]

**M2 — foreign safetensors importer (bite 1: the parser).** anukulana parses a
foreign **safetensors** checkpoint sovereignly — the first step toward importing a
real GPT-2 checkpoint and running it on rupantara.

### Added
- **`src/safetensors.cyr`** — `st_open` parses the `[u64 LE header_len][JSON
  header][tensor data]` layout into a bounds-checked tensor directory. **The JSON
  header is parsed by `bayan`** (the sovereign JSON DOM: `bayan_json_v_parse_str` +
  `bayan_json_v_obj_*`/`_arr_*`/`_str`/`_int`) — no hand-rolled JSON. Accessors:
  `st_count` / `st_entry` / `st_entry_{name,dtype,ndim,dim,nelems,data}` / `st_find`;
  `st_read_f64` reads a tensor into an f64 buffer, widening per dtype.
- **IEEE-754 wideners** `_st_f32_to_f64` / `_st_f16_to_f64` / `_st_bf16_to_f64`
  (verified absent from the ecosystem — candidate to promote into rosnet), plus LE
  readers `_st_u{16,32,64}_le`.
- **Untrusted-input safe:** header length bounds-checked; every tensor's
  `data_offsets` validated within the buffer; malformed / truncated / overrun
  buffers → `st_open` returns 0 (no OOB deref); `__metadata__` skipped.
- **`tests/tcyr/safetensors.tcyr`** (30 assertions): wideners on known bit patterns
  (F32/F16/BF16 → bit-exact f64) + a full parse round-trip (2 tensors: F64 bit-exact
  and F32 widened bit-exact, `__metadata__` skipped, truncated/overrun rejected).
  Suite 9 → **39**.

- **Forward stack wired** — `[deps.rupantara]` 0.4.0 + `[deps.rosnet]` 0.2.0 +
  stdlib `math`/`ganita`. `ru_model_fwd` / `ru_cfg_init` / `linear_fwd` now callable.
- **`src/gpt2.cyr` — GPT-2 → rupantara mapping (bite 2).** `anuk_gpt2_infer_cfg`
  (reads V/C/T/NL from tensor shapes; nh supplied) + `anuk_gpt2_pack` (packs an
  imported checkpoint into rupantara's layout via *its own* `_ru_o_*`/`_p_*`
  offset helpers). **Weight convention verified against rosnet `linear_fwd`
  source: it is `[in,out]` `y=x@W` — the same as GPT-2's Conv1D — so NO transpose**
  (nanoGPT transposes only because it targets `nn.Linear`). The one real remap is
  the **fused-QKV column split** (`c_attn` `[C,3C]`→Wq/Wk/Wv, bias `[3C]`→bq/bk/bv);
  everything else is a direct copy (learned pos / tanh-GELU / weight-tied head all
  already match rupantara). fp16/bf16→f64 widening from bite 1.
- **`tests/tcyr/gpt2.tcyr` (10 assertions) — self-contained round-trip fidelity.**
  Build a model in rupantara's layout → export as GPT-2-named safetensors (header
  built by **bayan**, Q/K/V fused) → import back → assert (a) packed params
  **bit-identical** and (b) `ru_model_fwd` logits **bit-identical** to the direct
  forward. Suite 39 → **49**.

### Remaining (M2)
- **Bite 3 (headline):** import a *real* GPT-2-small safetensors + match the
  reference (HF / nanoGPT `from_pretrained`) logits on a fixed input — needs the
  external checkpoint + fp32 payload (wideners + mapping already proven here).
  Then LoRA (M3) — two low-rank `rosnet.linear` passes (FD-gated).

## [0.1.0] — 2026-07-02

**M1 — consume tula (weight-file I/O).** anukulana reads the sovereign weight
format: `inspect <file.tula>` opens a checkpoint, enumerates its tensors
(name / dtype / shape / bytes), and reports/verifies its Ed25519 signature.
Untrusted-input safe — `tula_read_file` fully validates before any accessor, and a
missing/malformed file fails cleanly (rc=1, no crash).

### Added
- **tula + sigil wired** (`[deps.tula]` 1.0.0 + `[deps.sigil]` 3.9.9; stdlib set =
  the tula+sigil consumer union + `args`/`flags`). `src/inspect.cyr`:
  `anuk_inspect` (open + report + enumerate), `anuk_enumerate` (list tensors),
  `anuk_verify` (Ed25519 verify / tamper-reject), plus local dtype-name + decimal
  printers.
- **`inspect` + `version` subcommands** (`src/main.cyr`, `argc`/`argv` dispatch).
- **`tests/tcyr/tula_io.tcyr`** (8 assertions): build+sign a checkpoint → read as
  untrusted → enumerate (2 tensors) → verify OK / wrong-key rejected → payload-ok
  guard → tensor round-trips bit-exact. Suite 1 → **9**. CLI `anukulana inspect`
  verified end-to-end on the signed fixture.

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
