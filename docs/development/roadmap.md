# anukulana — Roadmap (1.x)

> **For an agent picking this up cold.** Read this, `CLAUDE.md` (conventions) and
> `docs/adr/0001-anukulana-scope.md` (scope). anukulana is the Type-3 pretrained-import
> **reference binary**: it consumes tula (format), rupantara (forward), rosnet (tensors) and
> sigil (Ed25519), and does not reinvent them.
>
> **Where it stands (1.4.0, 2026-11-09).** The whole charter is built and gated on the real GPT-2
> checkpoint: import (safetensors and GGUF, bit-identical across both), run, match HF
> (`gpt2-oracle`), adapt (LoRA, QLoRA/NF4) and persist (signed tula files). All seven commands were
> re-proven at the current pin in 1.3.0, and 1.4.0 shipped the tula 1.2–1.6 surface (checked adds,
> signed metadata and provenance, `inspect --pk`, big-file reads, streaming writes). The API froze at
> 1.0.0. This file lists **remaining work only**. Shipped work is in the
> [CHANGELOG](../../CHANGELOG.md), [`state.md`](state.md) and the audits
> ([2026-07-04](../audit/2026-07-04-audit.md), [2026-11-09](../audit/2026-11-09-audit.md)).

---

## Working agreement

- **Build/test:** `make build` · `make test` · the Cyrius pin and dependency tags are in
  `cyrius.cyml`.
- **Binary layout:** `main()` only in `src/main.cyr`; `src/lib.cyr` is the shared include chain.
  New module → `src/lib.cyr` (order). LSP "undefined" across flat modules is expected; the build is
  authoritative.
- **Definition of done each bite:** `make test` green · `make fmt-check` clean · `make lint` no
  `warn ` (lines ≤ 120) · `make vet` · `make doc` (every public fn documented) · CHANGELOG
  `[Unreleased]` updated.
- **Do NOT bump VERSION or run git** — the maintainer cuts releases.

## Discipline

- Cyrius-native, no BLAS/libc/autodiff. **FD-gate any new gradient.**
- The import is gated by **logit fidelity against the reference implementation**
  (`gpt2-oracle`). Honest negatives are reported, not hidden (4-bit drift, fp32 rounding).
- **Optimizations keep every output bit-identical** (as in 1.2.2), held by an equivalence test.
- **A new foreign-input parser lands with its fuzz rounds in the same cut**, against an image
  flush with an unmapped guard page, and every length or offset is checked wrap-safe before use
  (the 2026-07-04 audit's standing guidance, sharpened by 2026-11-09's).
- **Reproduce a defect on the old code before fixing it**, and pin the fix with a test that fails
  without it.

## Standing decisions

- **The LoRA head adapter is M3's adaptation proof** (user, 2026-07-04). Deeper, per-layer adapters
  need a transformer backward chain. That chain is **attn11's**: attn11 may be patched for arc needs,
  with one exception, **no SIMD work in attn11** (SIMD-shaped needs wait for the toolchain).
- **NF4 import-quantization is anukulana's; QAT-from-scratch is tentib's** (tentib ADR 0001). The
  base NF4 codec is **tula's**; only the superblock-256 double-quantization of the scales is local.
- **Dependencies are consumed, not forked.** A defect in a dependency is reported to its repo with a
  reproduction; anukulana carries at most a documented guard, never a patched copy.

---

## 1.3.x — follow-through on GitHub

1.3.0 re-proved every real-checkpoint gate locally, added the CI jobs below and froze the 1.2.2 helpers
(see the CHANGELOG). What is left can only be confirmed on GitHub:

- **The first `realweights.yml` run** (manual trigger; it fetches the 548 MB checkpoint once, then
  caches it). ⚠ The maintainer's call whether to add a schedule. It covers five of the seven commands;
  `gpt2-gguf` / `gpt2-cross` stay local because their GGUF comes from a Python converter.
- **The first runs of the `bounds` and `aarch64` CI jobs.** Both suites were green by hand (aarch64
  under qemu). The native runner label `ubuntu-26.04-arm` is taken from tula's CI and hasn't run
  for anukulana yet; if it isn't available, the job (and the release gate, which calls `ci.yml`) fails
  until it's changed.

## 1.5.x — keep the source precision (`convert`)

**Goal:** tula ADR 0005's premise, that "the Type-3 import path (anukulana) needs to keep the
source precision", rather than only writing NF4.

- **A `convert <model.{safetensors,gguf}> <out.tula> [--sk <key>]` command.** Write the imported
  weights as a signed tula file in their source dtype (F32, F16 or BF16, tula 1.3.0), with the
  architecture, config and provenance in its metadata (the `anukulana.*` keys the savers already write),
  plus the Hugging Face `config.json` beside the model as `hf.config` (ADR 0008's suggested namespace).
- **Load a converted file** straight into rupantara's packed layout, so a foreign file is parsed
  once and every later run starts from the signed sovereign copy.
- **Acceptance:** foreign file → `convert` → load lands on packed params bit-identical to the direct
  foreign import, for both doors. The widen is exact, so this is a `gpt2-cross`-style 0-diff gate.

## 1.6.x — onto rupantara 0.6–0.7 (gated on rupantara)

Each item lands when rupantara ships it (its roadmap, 0.6.x and 0.7.x, lists these as cross-repo
items for anukulana).

- **Drop the run-length repack.** `anuk_gpt2_import` re-packs the whole parameter buffer (about 1 GB
  for GPT-2 small) for every `T_run`. Move onto `ru_model_fwd_n` / `_n_s` once they land.
- **The config descriptor's growth path.** anukulana sizes every `cfg` at 64 bytes, stores it in
  checkpoints as F64 `[8]`, and its public entries take a caller-allocated `cfg`. If rupantara grows
  the descriptor:
  - the in-repo allocations move to rupantara's size function;
  - the checkpoint gains the new fields additively (a metadata key or a new tensor);
  - **a caller-visible size change in anukulana's own API is a 2.0 item** — agree the path with
    rupantara before 0.7 freezes it.
- **The layout helpers.** anukulana's source uses 29 of rupantara's underscore helpers (`_cfg_*`,
  `_ru_o_*`, `_p_*`, `_b?`, `_ru_blk_base`) as its layout API (counted at 1.2.2; rupantara's audit
  counted 22 before `_cfg_bias` and a few others were in use). Move onto public names if rupantara
  adds them, or record the frozen underscore set.
- **The allocating entries.** `gpt2-oracle` and `gpt2-cross` still call the allocating
  `ru_model_fwd`: 3 and 2 calls, bounded. Move them to `ru_model_fwd_s` if rupantara deprecates it.
- **Be rupantara's 1.0 consumer gate.** Run the fidelity gate and `gpt2-tula` against each
  `1.0.0-rc.N` (rupantara's 1.0 criterion: "≥1 downstream consumer green on a real model").
- **Acceptance:** no repack per run length; anukulana green on rupantara's release candidate.

## 1.7.x — quantized GGUF payloads

**Goal:** the GGUF door reads llama.cpp's quantized files, which today reject cleanly by type.

- **Dequantize the common GGML block types at import**, Q8_0 and Q4_0 first, then the K-quants,
  into the f64 layout. Fuzz rounds in the same cut, with block-size and extent checks before any read.
- **Report the fidelity honestly**, as `gpt2-qlora` does for NF4: weight error, logit drift and
  argmax agreement against the F32 import of the same checkpoint.
- **Keep the codes packed on disk** where tula can hold them: Q4 as tula int4 once tula 1.8 ships it
  (gated on tula), so `convert` does not widen 4-bit data.
- **Acceptance:** a llama.cpp-quantized GPT-2 imports and runs, batch == decode bit-identical, with its
  drift recorded; every new block reader is fuzz-gated.

## 1.8.x — llama-architecture import (gated on rupantara's architecture breadth)

**Goal:** TinyLlama-class models through both doors. The parsers already handle the files; what is
missing is the forward and the mapping.

- **Needs from rupantara** (its backlog, "Architecture breadth"): RoPE positions, RMSNorm, the
  SwiGLU MLP, an untied LM head (GQA exists), and the extended config from its 0.7.x.
- **anukulana side:** a llama mapping for GGUF (`llama.*` KVs, `blk.N.*`) and for HF safetensors
  (`model.layers.N.*`, with the config taken from `config.json` beside it). Add a committed fidelity
  fixture for a small llama-architecture checkpoint, generated once, as `gen_fixture.py` was.
- **Memory:** f64 params are 8 bytes per weight (8.8 GB at 1.1B). That fits a large machine but
  motivates the 2.0 item below. NF4 checkpoints of this class fit tula's normal writer.
- **Acceptance:** argmax-exact against the reference on the fixture; batch == decode; LoRA/QLoRA
  adapt over the import.

## 1.x.x — later (unscheduled, demand-gated)

- **The head-adapter training step: about 30 ms, 24 s for 800 steps** (1.3.0 profile, T=8, C=768,
  V=50257, r=8), so it is now most of `gpt2-lora` (26.6 s), `gpt2-qlora` and `gpt2-tula`. It is about
  2.6× slower per step than at 1.0, from the toolchain and dependency moves, not anukulana code. The two
  biggest pieces:
  - `ru_softmax_fwd` over the 402k logits, 10.0 ms, bound by ganita's `f64_exp` (about 14 ns each).
    That's rupantara's and ganita's: report it with these numbers. A faster `exp` changes bits, so it
    needs their parity policy first.
  - `lora_adam` on B (402k params), 9.1 ms. This one is anukulana's. Bit-identical first: hoist the
    per-element `1 − β` subtractions out of the loop. Dividing by the bias corrections through a
    reciprocal would change bits, so it isn't allowed under the Discipline rule.

  (NF4 quantization, the 1.0 hot spot at about 25 s, is now about 4.7 s in tula 1.6.1's codec: no
  longer the bottleneck.)
- **Text in, text out.** Wire **akshara** (the GPT-2 BPE) for a prompt → greedy-continuation command.
  It stays greedy: the sampler zoo is the Type-2 reference's, per rupantara's scope.
- **Per-layer LoRA adapters** — consumes attn11's backward chain (see Standing decisions).
- **A packed quantized forward** (dequantize inside the matmul). Needs quantized linears in rosnet;
  until then quantized weights widen at load.
- **Big-file signing speed** is bound by sigil's SHA-512 (about 18 MB/s, per tula). That is sigil's
  to fix; anukulana benefits with no change.
- **Duplicate tensor names in a safetensors header.** The first match wins today. Detecting duplicates
  needs a hash index to stay linear on hostile headers.
- **Pin CI's cyrius installer to the release** instead of `main`: an ecosystem-wide decision.

## 2.0.0 — backlog (only what 1.x can't carry)

A 2.0 breaks the frozen surface (`docs/api.md`, `STABILITY.md`), so it collects only changes with no
additive path. Nothing here is scheduled.

- **Source-precision (or f32) packed params.** Every import entry returns an f64 buffer by contract:
  1 GB at 124M params, 8.8 GB at 1.1B. Needs f32 paths in rupantara and rosnet first.
- **A larger caller-owned config,** if rupantara's descriptor grows and no compatible path exists
  (see 1.6.x).
- **Architecture-generic entry points** (`anuk_import(path, arch, …)` and one `import`-style CLI)
  replacing the GPT-2-named functions and commands. Add them alongside, as aliases, through 1.x once a
  second architecture exists (1.8.x); only removing the old names is 2.0.
- **Checkpoint layout v2:** the config and provenance in tula metadata only, retiring the frozen
  `"cfg"` F64 tensor, and an adapter layout for per-layer adapters if the 1.x names can't extend
  additively.

---

## Gates / relations

- **Dependencies** (all released; tags in `cyrius.cyml`): tula · rupantara · rosnet · sigil ·
  stdlib bayan / math / ganita. akshara is not wired yet (1.x.x).
- **Upstream gates on this plan:** rupantara 0.6 / 0.7 / 1.0 (1.6.x), rupantara's architecture breadth
  (1.8.x), tula 1.8 int4 (1.7.x), rosnet quantized linears (1.x.x). Larger models will want rosnet's
  mabda GPU profile (deferred).
- **Outstanding cross-repo asks addressed to anukulana:** tula — the real-weights gate in CI (the
  workflow landed in 1.3.0; its first run is pending, 1.3.x). Its 1.2–1.6 calls (checked adds, strict
  reads, streaming writes, metadata, long-name lookups) are adopted as of 1.4.0. rupantara —
  drop the repack and be the 1.0 consumer gate (1.6.x).
  Already done in 1.2.2: decode on `ru_model_fwd_row_s`, `RU_ERR_*` checked, off rupantara 0.4.2.
- **Boundary:** training/backward → attn11 · QAT → tentib · the format → tula · the forward →
  rupantara · sampling beyond greedy → the Type-2 reference. Rotation-PTQ and one-shot sparsity stay
  research-watch.
- **Ecosystem:** gap #1's importer — the AGNOS planning docs `type3-weight-import.md` +
  `software-port-path.md`.
