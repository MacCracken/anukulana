# Changelog

All notable changes to `anukulana` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); SemVer (pre-1.0 — surface still
moving, no API freeze until v1.0).

## [Unreleased]

**M3 bite 1 — LoRA over the frozen imported base (head adapter).** The adaptation
milestone opens: a low-rank pair fine-tunes the real imported GPT-2 while the
124M base params stay bit-frozen — gradients route ONLY into A,B via **two
ordinary `rosnet.linear_bwd` passes, no new gradient op** (the plan's exact
letter; the naive `dL/dA = Bᵀ·dL/dZ` trap avoided by construction).

### Added
- **`src/lora.cyr`** — the M3 primitive set: `lora_init` (A gaussian / B zero →
  ΔW = 0 at step 0) · `lora_fwd` (`y += s·(x·A)·B`, caches `u`) · `lora_bwd`
  (two `linear_bwd` passes → dA/dB accumulate) · `lora_merge` (`W += s·A·B`,
  untied matrices only) · softmax-xent loss/grad (`lora_xent_loss`/`_bwd`) ·
  `lora_sgd` + **`lora_adam`** (hand-derived, bias-corrected).
- **`tests/tcyr/lora.tcyr`** (5, suite 49→**54**) — the **FD gate**: every entry
  of dA AND dB vs central finite differences through the full
  base+adapter+xent forward (rel < 1e-5); B=0 ⇒ adapter output bit-identical;
  merge parity < 1e-12; a 50-step SGD training smoke descends.
- **`gpt2-lora <model.safetensors>`** CLI + `src/lora_demo.cyr` — the
  measurable-adaptation proof on the real checkpoint: head adapter
  (logits += s·(f·A)·B over the frozen forward's final-LN features f, computed
  ONCE — every step is head-sized), next-token-memorization objective. Result:
  **xent 10.79 → 0.0000 (800 Adam steps, r=8, lr=1e-2); greedy argmax 1/8 →
  8/8; base params xor-checksum unchanged; adapter-off logits bit-identical**
  (the fidelity gate still holds with the adapter off).

### Findings
- **Plain SGD diverges on the real checkpoint at ANY flat lr** — GPT-2's
  final-LN features carry massive-activation outlier dims (the same phenomenon
  behind the ganita `f64_tanh` overflow), making `dA = fᵀ·du` orders hotter on
  those dims. **Adam's per-parameter scaling is the remedy** (and what LoRA is
  actually trained with) — hence `lora_adam`. The toy-scale tcyr trains fine on
  SGD; the divergence is a real-data phenomenon.
- **Head-adapter scope is deliberate (bite 1):** on the weight-tied head the
  gradient path needs NO transformer backward chain (dL/dlogits is direct), so
  the "two linear_bwd passes" claim holds exactly. The adapter stays UNMERGED
  (merging into tied tok_emb would also rewrite the input embedding). Deeper
  per-layer adapters need a backward chain through the tail of the network —
  scope question flagged in the roadmap (that chain is attn11's territory).

## [0.3.0] — 2026-07-04

**M2 fidelity gate — the imported GPT-2 forward matches HF exactly (M2 COMPLETE).**
The last M2 correctness check lands: `gpt2-oracle` gates the sovereign forward
against a **committed HF-reference fixture**, closing the "needs a torch oracle
staged" gap without ever making Python/torch a dependency — the oracle ran ONCE in
a disposable venv and its output is committed as test data.

### Added
- **`src/oracle.cyr`** — `anuk_gpt2_oracle(model, fixture)`: reads the fixture
  (bounds-checked: magic / n_seqs / uniform-T / payload-overrun rejected), imports
  the checkpoint once, and for each sequence gates (a) **per-position argmax ==
  HF's exactly** (the greedy stream is identical), (b) **last-position logits
  maxrel ≤ 1e-5** (denominator floored at 1.0), (c) NaN-free. HF computes fp32,
  we compute f64 over the same f32-widened weights, so the measured diff is HF's
  own fp32 rounding — bit-exact is impossible by construction.
- **`gpt2-oracle <model.safetensors> <fixture.bin>`** CLI command + usage lines;
  `make fidelity` target (`GPT2_MODEL` overridable).
- **`tests/fixtures/gpt2_oracle_v1.bin`** (1.2 MB, committed) — 3 deterministic
  16-token sequences (no tokenizer — integer patterns; seq 0 = the `gpt2`
  command's existing pattern): per-position HF argmax + last-position HF logits
  (fp32→f64). Format v1 documented in `src/oracle.cyr` + the generator.
- **`tests/oracle/gen_fixture.py`** — the one-shot generator (committed for
  reproducibility only; disposable-venv instructions in its docstring).

### Result (real 124M checkpoint, 2026-07-04)
- **argmax exact at all 48 positions** (3 seqs × 16); NaN 0.
- last-row **maxabs ≤ 1.03e-4** on logits O(100); **maxrel ≤ 1.05e-6** —
  fp32-rounding scale, as predicted. Gate frozen at maxrel ≤ **1e-5** (10× above
  measured). Suite unchanged (39/39 + tula_io); lint/fmt clean.
- M2 is **fully complete**; next is **M3 — LoRA** (FD-gate the A,B path).

## [0.2.0] — 2026-07-02

**M2 — the foreign importer works on a real model.** anukulana imports a real
**GPT-2-small** safetensors checkpoint and runs its forward through rupantara: parse
(bayan JSON DOM) → fp32/f16/bf16→f64 widen → GPT-2→rupantara layout map (fused-QKV
split, no transpose) → `ru_model_fwd`. Verified on HF's actual 124M checkpoint.
Along the way it surfaced + fixed a real ecosystem bug (ganita `f64_tanh` NaN
overflow). Additive over 0.1.0 (new `safetensors` / `gpt2` surface; no breaking change).

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

- **Bite 3 — real GPT-2-small imports + runs cleanly. ✅** `src/safetensors.cyr`
  `st_open_mmap` (zero-copy mmap; the 548 MB file + ~1 GB params both exceed the
  256 MB `ALLOC_MAX`, so file → `mmap_file_ro`, params → `mmap_anon`);
  `anuk_gpt2_import` (mmap → infer_cfg → override context → pack); `gpt2` CLI
  subcommand. Verified on the **real HF gpt2 checkpoint** (548 MB / 148 tensors,
  fp32): config inferred (V=50257 C=768 NL=12), **0 NaN in 123.6 M widened
  params**, **batch forward == KV-cache decode bit-identical**, and **logits
  finite** (real next-token argmax). Runs in ~3.7 s.
- **Toolchain pin 6.3.27 → 6.3.31.** Bite 3 first surfaced a real bug —
  `ganita_f64_tanh` overflowed to `inf/inf`=NaN for |x|>~709, which GPT-2's GELU
  `x³` hits on massive-activation outliers (localized to block 2, one position).
  Fixed in **ganita 1.0.2** (saturate for |x|>20, bit-exact); cyrius **6.3.31**
  re-folded it, and pinning here picks it up — the forward is now clean. Filed:
  `docs/development/issues/2026-07-02-ganita-f64-tanh-overflow.md`.

### Remaining (M2)
- **Exact fidelity gate:** real GPT-2 logits vs HF `from_pretrained` on a fixed
  input — needs a torch oracle staged (not installed here). The import + forward
  are proven; this is the last correctness check. Then LoRA (M3) — two low-rank
  `rosnet.linear` passes (FD-gated).

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
