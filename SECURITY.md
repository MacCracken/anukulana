# Security Policy — anukulana

## Threat model

anukulana's job is to consume **untrusted foreign model files** and to
produce/consume **signed sovereign checkpoints**. The attack surfaces, and
their defenses:

1. **Foreign safetensors input** (`st_open` — attacker-controlled bytes).
   Header length bounds-checked against the buffer; JSON header parsed by
   **bayan** (the sovereign DOM, not hand-rolled scanning); every tensor's
   `data_offsets` validated within the payload; ndim capped (≤8); malformed /
   truncated / overrun input → clean reject (returns 0, no OOB dereference).
   *(1.2.2)* Every dim and offset must be a JSON integer, dims non-negative with
   a product that can't wrap, and a fixed-width tensor's payload exactly
   shape × element size — so no read sized from the shape can leave the
   payload. Through 1.2.1 the shape was never compared with the payload, and
   `shape [1e8]` over 4 bytes crashed the reader (2026-11-09 audit, HIGH #1).
   **Fuzz-gated**: `tests/tcyr/fuzz.tcyr` runs 55k+ deterministic
   byte-mutation, header-digit-mutation, truncation-sweep and garbage-buffer
   rounds, each image flush against an unmapped guard page, and reads every
   tensor an accepted reader lists.
2. **Foreign GGUF input** (`gg_open` — attacker-controlled bytes; added 1.x).
   Same discipline as `st_open`, applied from line one: magic/version gate
   (v2/v3 only), typed-KV walk with structural skip (unknown value-type ids
   hard-reject — their size is unknowable), every length/offset checked
   wrap-safe before use, alignment restricted to powers of two 8–65536,
   per-tensor extents validated inside the data section, sanity caps (64k
   tensors/KVs, 2^30 per dim, 2^29 elems — the element count checked at every
   multiply since 1.2.2, when four in-cap dims could wrap to 4), every KV read
   at its own width (1.2.2: a u16 was read with a 4-byte load), allocations
   sized from foreign data null-checked. F32/F16 payloads, *(1.6.0)* the legacy
   block types Q4_0/Q4_1/Q5_0/Q5_1/Q8_0 and *(1.6.1)* the K-quants Q2_K–Q6_K are
   consumed; every other GGML type id rejects cleanly. A block tensor's `ne0` must be whole blocks
   and its payload exactly blocks × block bytes, checked before any read, and a
   decoder reads only the blocks a range touches. The 1.6.0 fuzz rounds (30k byte
   mutations of a five-type image, 20k structure-aware mutations of `ne0`, the type
   and the data offset, a truncation sweep, random sub-range reads) run against a
   guard page; two over-read mutants of the decoder and the extent check fault
   there. *(1.6.1)* The same rounds run over a five-K-quant image (ne0 = 512, two
   superblocks each), and a Q6_K over-read mutant faults there. **Fuzz-gated in the same cut**: 30k byte-mutation
   rounds + a full truncation sweep + 5k garbage buffers, guard-paged, reads
   on every accepted reader. *(1.2.2)* The GPT-2 mapping requires every weight
   to have exactly its expected shape: through 1.2.1 a weight with extra output
   rows overflowed a heap scratch (2026-11-09 audit, HIGH #2).
3. **Sovereign checkpoints** (`.tula` files). Structural validation is
   **tula's** (`tula_open` — its own frozen, fuzzed surface); authenticity is
   **Ed25519 via sigil**: `anuk_nf4_load` / `anuk_adapter_load` verify the
   signature and **reject unsigned, wrong-key, and tampered files** (gated in
   `tests/tcyr/nf4_store.tcyr`). *(1.2.2)* Both also run tula's strict
   validator (exact payload sizes, no duplicate names) and require every tensor
   to have exactly its layout's dtype and shape before reading it — a signature
   proves who wrote a file, not that it is well-formed. Key management is the
   caller's (per tula's charter); the demos use ephemeral keys.
   `anuk_sk_load` *(1.2.2)* accepts only an exact 64-byte seed‖pk whose public
   half is derived from its seed. *(1.4.0)* Files carry signed metadata
   (provenance: the source model's SHA-256, and for an adapter its base
   checkpoint's), so tampering with the description is as detectable as with
   the weights; `inspect --pk` verifies from the CLI and fails an unsigned file
   as firmly as a bad signature.
4. **The oracle fixture** (`_orc_read_fixture`). Committed test data, but read
   defensively anyway: magic + count/shape bounds + payload-overrun checks;
   included in the fuzz suite.
5. **Large-file handling.** >256 MB inputs are mmap'd read-only (`st_open_mmap`,
   `gg_open_mmap`) — no unbounded heap reads; `tula_read_file` carries tula's
   bomb-guard. A rejected file is unmapped again (1.2.2).
6. **The model config built from a file** (added 1.2.1). Every config that comes
   from file contents passes rupantara's `ru_cfg_check` before anything is sized
   from it. That covers GGUF KV metadata (`head_count`, `block_count`,
   `feed_forward_length`), safetensors tensor shapes and the signed checkpoint's
   `cfg` tensor. The check refuses zero or negative dims, `C % nh != 0`,
   `nh % nkv != 0` and any size that would wrap an i64. Through 1.2.0 nothing
   checked: `head_count = 0`, or `nh = 0` in a correctly signed checkpoint,
   divided by zero inside `ru_params_count` (SIGFPE). Gated in
   `tests/tcyr/gguf.tcyr`, `gpt2.tcyr` and `nf4_store.tcyr`.
7. **Converted model files** (added 1.5.0). `anuk_tula_import` treats a converted
   file like every other signed input: tula's strict validator, then the Ed25519
   signature (`tula_verify_required` — an unsigned file is rejected), then the
   file's `anukulana.kind` / `.layout` and its `"cfg"` (through `ru_cfg_check`),
   then the same exact-shape mapping as the safetensors door. Files that
   `convert` signs with the demo key (no `--sk`) prove integrity, not authorship:
   the key's seed is in the source. The signature is checked on every load
   (about 27 s for GPT-2 small at sigil's current SHA-512 speed); no faster path
   skips it.
8. **The GPT-2 mapping's shape contract** (added 1.2.2). Both mappings check every
   tensor's exact rank and dims, not just its element count, so a transposed or
   re-shaped weight is rejected instead of being imported as garbage.

The full 1.2.2 findings, with reproductions and mutation results, are in
[`docs/audit/2026-11-09-audit.md`](docs/audit/2026-11-09-audit.md).

Out of scope: the underlying crypto (sigil's audit surface), the tula format
internals (tula's), memory-safety of the caller-guarantees tensor substrate
(rosnet's audited contract), and adversarial *model weights* (a checkpoint that
signs/parses cleanly but computes something malicious is a policy question for
the serving layer — hoosh/kavach — not the importer).

## Reporting

Open an issue at <https://github.com/MacCracken/anukulana/issues> (or contact
the maintainer privately for sensitive reports). Include a minimal reproducing
input where possible; the fuzz harness accepts replay seeds.
