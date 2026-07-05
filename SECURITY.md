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
   **Fuzz-gated**: `tests/tcyr/fuzz.tcyr` runs 35k+ deterministic
   byte-mutation, truncation-sweep, and garbage-buffer rounds against the
   parser plus accessor probes on every accepted reader.
2. **Foreign GGUF input** (`gg_open` — attacker-controlled bytes; added 1.x).
   Same discipline as `st_open`, applied from line one: magic/version gate
   (v2/v3 only), typed-KV walk with structural skip (unknown value-type ids
   hard-reject — their size is unknowable), every length/offset checked
   wrap-safe before use, alignment restricted to powers of two 8–65536,
   per-tensor extents validated inside the data section, sanity caps (64k
   tensors/KVs, 2^30 per dim, 2^29 elems), allocations sized from foreign data
   null-checked. Only F32/F16 payloads are consumed; quantized GGML block
   types reject cleanly. **Fuzz-gated in the same cut**: 30k byte-mutation
   rounds + a full truncation sweep + 5k garbage buffers, accessor probes on
   every accepted reader.
3. **Sovereign checkpoints** (`.tula` files). Structural validation is
   **tula's** (`tula_open` — its own frozen, fuzzed surface); authenticity is
   **Ed25519 via sigil**: `anuk_nf4_load` / `anuk_adapter_load` verify the
   signature and **reject unsigned, wrong-key, and tampered files** (gated in
   `tests/tcyr/nf4_store.tcyr`). Key management is the caller's (per tula's
   charter); the demos use ephemeral keys.
4. **The oracle fixture** (`_orc_read_fixture`). Committed test data, but read
   defensively anyway: magic + count/shape bounds + payload-overrun checks;
   included in the fuzz suite.
5. **Large-file handling.** >256 MB inputs are mmap'd read-only (`st_open_mmap`,
   `gg_open_mmap`) — no unbounded heap reads; `tula_read_file` carries tula's
   bomb-guard.

Out of scope: the underlying crypto (sigil's audit surface), the tula format
internals (tula's), memory-safety of the caller-guarantees tensor substrate
(rosnet's audited contract), and adversarial *model weights* (a checkpoint that
signs/parses cleanly but computes something malicious is a policy question for
the serving layer — hoosh/kavach — not the importer).

## Reporting

Open an issue at <https://github.com/MacCracken/anukulana/issues> (or contact
the maintainer privately for sensitive reports). Include a minimal reproducing
input where possible; the fuzz harness accepts replay seeds.
