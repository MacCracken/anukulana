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
   sized from foreign data null-checked. Only F32/F16 payloads are consumed; quantized GGML block
   types reject cleanly. **Fuzz-gated in the same cut**: 30k byte-mutation
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
7. **The GPT-2 mapping's shape contract** (added 1.2.2). Both mappings check every
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
