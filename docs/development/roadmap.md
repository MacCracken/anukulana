# anukulana — Roadmap (1.x)

> **For an agent picking this up cold.** Read this, `CLAUDE.md` (conventions) and
> `docs/adr/0001-anukulana-scope.md` (scope). anukulana is the Type-3 pretrained-import
> **reference binary**: it consumes tula (format), rupantara (forward), rosnet (tensors) and
> sigil (Ed25519), and does not reinvent them.
>
> **Where it stands (1.6.0, 2026-11-09).** The whole charter is built and gated on the real GPT-2
> checkpoint: import (safetensors and GGUF, bit-identical across both), run, match HF
> (`gpt2-oracle`), adapt (LoRA, QLoRA/NF4) and persist (signed tula files). All seven commands were
> re-proven at the current pin in 1.3.0, and 1.4.0 shipped the tula 1.2–1.6 surface (checked adds,
> signed metadata and provenance, `inspect --pk`, big-file reads, streaming writes). On GitHub, the
> real-weights workflow has run green, and so has the 1.4.0 release, which gates on the `bounds` and
> native `aarch64` CI jobs. 1.5.0 shipped `convert` (a signed tula copy at source precision, both doors
> bit-identical) and `gpt2-load`. 1.5.1 moved onto rupantara 0.6.1: one full-context import serves every
> run length, and all nine real-checkpoint commands pass through it. 1.6.0 reads GGUF's legacy
> quantized block types (Q4_0 … Q8_0) exactly as ggml dequantizes them. The API froze at 1.0.0.
>
> **What is next (reprised 2026-11-09, after 1.5.1).** Every dependency is at its latest tag (cyrius
> 6.7.18; sigil 3.13.15, tula 1.6.1, rosnet 1.4.1, rupantara 0.6.1). rupantara's 0.6.x is complete, and
> its 0.7.x, which the old 1.6.x line waited on, has not started. So the order is now:
>
> 1. **1.6.x, quantized GGUF payloads** (moved up from 1.7.x). Nothing upstream blocks it. 1.6.0
>    shipped the legacy block types and the K-quants are in `[Unreleased]`; packed `convert` and a
>    steadier drift measure remain.
> 2. **1.7.x, onto rupantara 0.7 → 1.0.** What remains of the old 1.6.x line; it lands as rupantara
>    ships.
> 3. **1.8.x, the llama architecture.** It waits for rupantara's architecture breadth, which rupantara
>    schedules after its 1.0.
>
> This file lists **remaining work only**. Shipped work is in the [CHANGELOG](../../CHANGELOG.md),
> [`state.md`](state.md) and the audits ([2026-07-04](../audit/2026-07-04-audit.md),
> [2026-11-09](../audit/2026-11-09-audit.md)).

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

## 1.6.x — quantized GGUF payloads (next: nothing upstream blocks it)

**Goal:** the GGUF door reads llama.cpp's quantized files.

**The decoders are done.** 1.6.0 shipped the legacy block types (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0). The
K-quants (Q2_K … Q6_K, so llama.cpp's standard mixes) are in `[Unreleased]`. Every type is checked
three ways:

- against gguf-py's `dequantize` on committed fixtures of random blocks;
- against ggml's own dequantization on all 124,439,808 params of a real GPT-2: 0 differ in each of
  the ten formats;
- by fuzz rounds against the guard page.

The real K-quant files come from llama.cpp's `llama-quantize`, built at test time at a pinned tag by
`tests/oracle/gen_kquants.sh` (the maintainer's call, 2026-11-09). What remains:

- **`convert` keeps the codes packed where tula can hold them.** Today it writes them as exact F32: the
  converted GPT-2 is 497.8 MB whatever the type, 3.7× the Q8_0 file and 6.8× the Q4_0 one.
  - **Q8_0:** tula `INT8` codes plus a per-block `w.scale` sidecar holding the f16 scales, which is
    lossless. tula's ADR 0002 lists per-tensor and per-row int8 scales, and NF4's scales are already
    per-block. The convention is the consumer's to own, so record it in `docs/api.md` and tell tula.
    The loader then decodes it as the GGUF door does.
  - **4-bit and K-quant data** waits for tula 1.8's int4 (gated on tula). Its ADR chooses between
    inline f16 scales and a sidecar.
- **A steadier drift measure.** `gpt2-qgguf` compares argmax over the 8-position demo input, whose
  top-1 / top-2 margins are 0.02 to 1.1 logits, so even Q5_1 agrees on only 2 of 8 and Q4_K_M on 6.
  Run it over the oracle fixture's 48 positions as well, and report the agreement with HF's argmax
  there.
- **The GGUF gates in CI (optional).** `gpt2-gguf`, `gpt2-cross` and `gpt2-qgguf` run locally only,
  because their files come from a Python venv and, now, a llama.cpp build (about 2 minutes). A
  `realweights.yml` job could make both. ⚠ The maintainer's call: it adds pip and cmake steps to a
  workflow that has none today.
- **Acceptance:** the Q8_0 convert is packed and lossless; the drift is reported over the 48 fixture
  positions.

## 1.7.x — onto rupantara 0.7 → 1.0 (gated on rupantara)

rupantara's 0.7.x settles the API shape that its 1.0 freeze will lock. It has not started: rupantara's
latest tag is 0.6.1, and its roadmap names 0.7.x as next. Each item lands in whichever anukulana minor
is current when rupantara ships it, so one that arrives during 1.6.x rides along there.

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
  adds them, or record the frozen underscore set. rupantara's 0.7.x item still says 22, so give it the
  current list when that work starts.
- **The allocating entries.** `gpt2-oracle` and `gpt2-cross` call the allocating `ru_model_fwd_n`
  (`ru_model_fwd` through 1.5.0): 3 and 2 calls, bounded. Move them to `ru_model_fwd_n_s` if rupantara
  deprecates the allocating entries.
- **Be rupantara's 1.0 consumer gate.** Run the fidelity gate and `gpt2-tula` against each
  `1.0.0-rc.N` (rupantara's 1.0 criterion: "≥1 downstream consumer green on a real model").
- **Acceptance:** anukulana is green on rupantara's release candidate, and each consumer change that
  rupantara's 0.7.x asks for ships in the anukulana release that adopts it.

## 1.8.x — llama-architecture import (gated on rupantara's architecture breadth)

**Goal:** TinyLlama-class models through both doors. The parsers already handle the files; what is
missing is the forward and the mapping.

- **Needs from rupantara** (its backlog, "Architecture breadth"): RoPE positions, RMSNorm, the
  SwiGLU MLP, an untied LM head (GQA exists), and the extended config from its 0.7.x. rupantara
  schedules architecture breadth after its 1.0, so this line follows 1.7.x.
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
- **Text in, text out — gated on akshara.** A prompt → greedy-continuation command. It stays greedy:
  the sampler zoo is the Type-2 reference's, per rupantara's scope.
  - **What akshara can't do yet** (1.3.1): it learns its own byte-level BPE from a corpus, at most 512
    merges in process-global state, and it cannot load a pretrained vocabulary.
  - **What GPT-2 needs:** its 50,000 merges over 50,257 tokens, the byte-to-unicode mapping and the
    pre-tokenizer split.
  - **Where the vocabulary is:** HF ships `vocab.json` and `merges.txt` beside the safetensors (not
    staged in `~/models/gpt2` yet). llama.cpp's GGUF carries them as `tokenizer.ggml.tokens` and
    `.merges`, though `gen_gguf.py` doesn't write them today.
  - **The ask:** akshara adds a pretrained-vocabulary mode. File it with akshara (tokenizing is
    akshara's, per ADR 0001); anukulana then adds the command.
- **Per-layer LoRA adapters** — consumes attn11's backward chain (see Standing decisions).
- **A packed quantized forward** (dequantize inside the matmul). Needs quantized linears in rosnet;
  until then quantized weights widen at load.
- **Big-file signing speed** is bound by sigil's SHA-512 (18.4 MB/s, measured here). That is sigil's to
  fix; anukulana benefits with no change. It is what makes `convert` take about 86 s and `gpt2-load`
  about 29 s on GPT-2 small (sign ~54 s, verify ~27 s for ~500 MB): file it with sigil, with these
  numbers.
- **A digest-pinned load for converted files** — ⚠ the maintainer's call, because it changes the trust
  model. For example, `gpt2-load --sha256 <hex>` would accept the file on a caller-pinned SHA-256
  (about 1.6 s at sigil's SHA-NI speed) printed at convert time, instead of verifying the Ed25519
  signature every run. Today every load verifies.
- **Duplicate tensor names in a safetensors header.** The first match wins today. Detecting duplicates
  needs a hash index to stay linear on hostile headers.
- **Pin CI's cyrius installer to the release** instead of `main`: an ecosystem-wide decision.
- **Schedule `realweights.yml`.** It is manual today, because each uncached run fetches the 548 MB
  checkpoint. Adding a `schedule:` trigger (the workflow's header shows one) is the maintainer's call.

## 2.0.0 — backlog (only what 1.x can't carry)

A 2.0 breaks the frozen surface (`docs/api.md`, `STABILITY.md`), so it collects only changes with no
additive path. Nothing here is scheduled.

- **Source-precision (or f32) packed params.** Every import entry returns an f64 buffer by contract:
  1 GB at 124M params, 8.8 GB at 1.1B. Needs f32 paths in rupantara and rosnet first.
- **A larger caller-owned config,** if rupantara's descriptor grows and no compatible path exists
  (see 1.7.x).
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
- **Upstream gates on this plan:**
  - rupantara 0.7 / 0.8 / 1.0 (1.7.x);
  - rupantara's architecture breadth, after its 1.0 (1.8.x);
  - tula 1.8 int4 (1.6.x, the 4-bit half of `convert`);
  - akshara, a pretrained vocabulary (1.x.x, text in, text out);
  - rosnet, quantized linears (1.x.x).

  Larger models will want rosnet's mabda GPU profile (deferred).
- **Outstanding cross-repo asks addressed to anukulana:**
  - rupantara: be its 1.0 consumer gate (1.7.x).
  - Met: rupantara's "drop the repack" (1.5.1, on 0.6.1). Also 1.2.2's decode on
    `ru_model_fwd_row_s` with `RU_ERR_*` checked, and the move off rupantara 0.4.2.
  - Met: tula's two asks. The real-weights gate runs in CI (`realweights.yml`, 1.3.0, green on
    GitHub), and its 1.2–1.6 calls are adopted (1.4.0).
- **Asks anukulana owes other repos.** None is filed yet, and each needs the maintainer's go:
  - **sigil:** SHA-512 throughput, 18.4 MB/s, with the `convert` and `gpt2-load` numbers (1.x.x).
  - **rupantara and ganita:** the `ru_softmax_fwd` / `f64_exp` cost in the adapter step (1.x.x).
  - **akshara:** a pretrained-vocabulary mode for GPT-2 (1.x.x).
  - **rupantara:** the layout-helper count is 29, not the 22 its 0.7.x item says (1.7.x).
  - **tula:** the per-block int8 scale convention, once 1.6.x uses it.
- **Boundary:** training/backward → attn11 · QAT → tentib · the format → tula · the forward →
  rupantara · sampling beyond greedy → the Type-2 reference. Rotation-PTQ and one-shot sparsity stay
  research-watch.
- **Ecosystem:** gap #1's importer — the AGNOS planning docs `type3-weight-import.md` +
  `software-port-path.md`.
