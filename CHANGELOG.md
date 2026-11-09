# Changelog

All notable changes to `anukulana` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); SemVer (pre-1.0 — surface still
moving, no API freeze until v1.0).

## [Unreleased]

## [1.2.1] - 2026-11-09

Moves anukulana to cyrius 6.7.18 and every dependency to its latest release. It also adopts
rupantara's new config check at the three places a model config is built from file contents,
which closes a hostile-input crash present through 1.2.0.

### Changed

- **Toolchain `6.7.9` → `6.7.18`** (through 6.7.10–6.7.17). rupantara 0.5.1 sums up the
  6.7.10–6.7.18 behaviour changes: almost all are new compile-time refusals (generics, struct
  and pointer shapes, enums), plus runtime changes in net, TLS, thread-local slots and pam.
  anukulana builds with no warning, uses none of net, TLS or pam itself, and lint stays at 0
  warnings under 6.7.11's and 6.7.12's new rules.
- **Dependencies moved to their latest tags** (checked against GitHub on 2026-11-09). rosnet
  1.4.1 and rupantara 0.5.3 are newer than the sibling checkouts on the verification host.
  - `sigil` stays at `3.13.15`. It is still sigil's latest tag, and now also the copy cyrius 6.7.18
    bundles, so 1.2.0's `./lib/ shadows … sigil` build warning is gone.
  - `tula` `1.1.0` → `1.6.1`: five additive minors (1.2.0 checked builders and error codes, 1.3.0
    long names and F32/F16/BF16, 1.4.0 big files, 1.5.0 lookup at scale, 1.6.0 signed file
    metadata) and two patches (1.1.2's hardening pass, 1.6.1). There is no format change. Every
    tula function anukulana calls keeps its signature, and tula reports their outputs unchanged.
  - `rosnet` `1.2.0` → `1.4.1`. No API change, and every CPU result is byte-identical per rosnet's
    15,302-line golden dump. 1.2.2 rewrote `linear_fwd` (about 2.7× faster at 64×768×768) and kept
    each output's rounding sequence. rupantara 0.5.1 checked that independently against its
    forward. 1.2.2 also makes `t_alloc(0)` return an empty tensor (it used to exit), and makes a
    negative or wrapping size exit with "invalid size". anukulana sizes its tensors from a checked
    config, so neither case is reached. tyche comes in transitively at `1.2.2` (was `1.2.0`), with
    the same bits for every state its API can reach.
  - `rupantara` `0.5.0` → `0.5.3`. No API change, and output is bit-identical for valid input.
    0.5.2 makes the model entries and the sizing functions validate the config (see Fixed). The
    private layout helpers anukulana calls (`_bq`, `_cfg_C`, `_ru_o_Wq`, …) are byte-identical to
    0.5.0's.
- **bayan in the 6.7.18 snapshot is `1.11.1`** (was `1.5.13`). Of the 18 `bayan_json_v_*`
  functions anukulana's source and tests call, only `_is_obj` and `_is_arr` changed signature:
  they now return `bool`. The existing `== 0` comparisons compile unchanged.
- **DCE binary 454,448 → 814,120 B, all of it data.** bayan 1.9.0 (folded into cyrius 6.7.13)
  requires `lib/unicode/`, about 300 KB of string tables, and DCE drops functions but not global
  initializers. anukulana calls bayan directly for the safetensors header, so it pays this
  whatever sigil does. tula 1.1.1 recorded the same jump.
- **`anukulana_version()` `10200` → `10201`.** The `smoke.tcyr` assertion moves with it.

### Fixed

- **A model config built from a file is checked before anything is sized from it.** rupantara
  0.5.2 added the public `ru_cfg_check`, and made `ru_params_count` / `ru_decode_kv_count` return
  `RU_ERR_CFG` (-1) for a config it rejects. Four places now call it right after `ru_cfg_init` and
  reject on failure: `anuk_ggpt2_infer_cfg`, `anuk_gpt2_infer_cfg`, `anuk_gpt2_import` (after it
  applies `T_run`) and `anuk_nf4_load`.
  - Through 1.2.0 nothing checked. A GGUF with `gpt2.attention.head_count = 0`, or a correctly
    signed NF4 checkpoint whose `cfg` tensor has `nh = 0`, divided by zero inside
    `ru_params_count`. Reproduced: the NF4 load, run under 1.2.0's deps, was killed by SIGFPE.
  - A safetensors `C` that isn't a multiple of 12 (`nh` is fixed at 12 on that path) used to run
    with a layout rupantara says leaves concat columns unwritten. It is rejected now too.
  - rupantara 0.5.3 alone already turns these into rejects (its -1 makes `mmap_anon` fail, or the
    stored-`np` check mismatch). The guard makes the rejection explicit, happens before any sizing
    and names the fault (`nf4-load: bad cfg`).
  - `SECURITY.md`'s threat model gains this as item 6.

### Added

- **10 assertions (suite 129 → 139).** `gguf.tcyr` 38 → 43: `head_count` patched to 0 and then to
  3 in an exported GGUF. `gpt2.tcyr` 10 → 12: `nh = 3` and `nh = 0` against `C = 4`.
  `nf4_store.tcyr` 21 → 24: a correctly signed checkpoint with `nh = 0` and well-formed base
  tensors, so the load reaches the sizing path.

### Verified

- **In-tree, git-first.** On a fresh `lib/` and `cyrius.lock`, `cyrius deps` commit-pinned all
  five deps: sigil `3c47656`, tula `09d469b`, rosnet `af2bb1a`, rupantara `83b6e74`, tyche
  `cdb74e2`. Every vendored `lib/<dep>.cyr` header was confirmed at its new version.
  `cyrius deps --verify` reports 69 verified and 0 failed, and `cyrius deps --locked` is clean.
- Suite **139/139** across 9 files. The build prints no warnings, lint has 0 `warn ` lines, fmt
  and vet are clean, and the DCE binary builds and runs (`version` prints `10201`).
- **The new tests catch a missing guard.** With the four `ru_cfg_check` lines removed, `gpt2.tcyr`
  and `gguf.tcyr` each fail 2 assertions. `nf4_store.tcyr` still passes, because rupantara 0.5.3's
  -1 rejects the load at the `np` check (`nf4-load: np/cfg mismatch`). The same guard-free load
  under 1.2.0's deps dies of SIGFPE.
- **Not run: `make fidelity` or the checkpoint demos.** The GPT-2 checkpoint is still not staged
  on the verification host. rosnet and rupantara report bit-identical CPU results, but the
  HF-logit gate has not been re-run since 1.1.3.

## [1.2.0] - 2026-11-09

Moves anukulana onto the cyrius 6.7 series and git-first dependency resolution. No behavior or API
change. The minor bump marks the toolchain line, as tula 1.1.0, rosnet 1.2.0 and rupantara 0.5.0 did.

### Changed

- **Toolchain `6.6.20` → `6.7.9`** (through 6.7.0–6.7.8). `src/` needed no change. Upstream changes
  checked against anukulana's `src/` and `tests/`:
  - **6.7.0–6.7.8** reserve `trait`, `const`, `true`, `false`, `do` and `dyn`. anukulana uses none of
    them outside comments and strings.
  - **6.7.3** makes `!` a real operator. Before that a lone `!x` compiled as `x`. anukulana has no `!`
    outside `!=`.
  - **6.7.9** makes unary `-` and `~` on a constant bind tighter, and **6.7.8–6.7.9** change how typed
    `*T` pointers step and dereference. anukulana has neither: its buffers are untyped addresses read
    with `load64` / `load32` / `store64`.
  - **6.7.6** rounds every write into an `f32`. anukulana has no `f32` variables. f32, f16 and bf16
    payloads are widened to f64 at the bit level (`_st_f32_to_f64` over a `load32`).
  - **6.7.6** folds `cyrius tests` into `cyrius test`. The Makefile and CI already run
    `cyrius test <file>` once per suite.
- **Dependencies moved to the releases built against 6.7.9.** None of them changes its source or API,
  and their stdlib sidecars are identical to the 6.6.20 set, so `[deps].stdlib` doesn't move.
  - `sigil` `3.13.10` → `3.13.15`. It pins 6.7.9 and is the sigil tula 1.1.0 pins. 3.13.11–3.13.15
    are additive-only for API, and the `ed25519_*` calls tula and `nf4_store` make are unchanged.
    The 6.7.9 toolchain bundles an older copy (3.13.11); see Notes.
  - `tula` `1.0.3` → `1.1.0`. The public surface and on-disk format v1 are exactly 1.0.3's.
  - `rosnet` `1.1.3` → `1.2.0`. rosnet's `src/` is unchanged, and it reports byte-identical f64
    results for every CPU op, `linear_fwd` / `linear_bwd` included. tyche comes in transitively at
    `1.2.0` (was `1.1.1`), with its source and stream unchanged.
  - `rupantara` `0.4.4` → `0.5.0`. The forward and API are unchanged. It pins rosnet `1.2.0` too, so
    the graph still resolves a single rosnet.
- **Git first.** Every build resolves the four dep tags, a dev box's included. The `path = "../x"`
  lines are now dev overrides, read only in local mode (`CYRIUS_LOCAL=1`, `CYRIUS_LOCAL=<dep,dep>`
  or `--local`). The "⚠ `path` SHADOWS `tag`" comment in `cyrius.cyml` is replaced with a git-first
  note, and the roadmap's 6.7.6 to-do is marked applied. Its `cyrius deps --locked` item doesn't
  apply: CI has no lock guard or path-stripping step, and `cyrius.lock` stays gitignored.
- **DCE binary 715,728 → 454,448 B.** sigil 3.13.12 shrank a 256 KiB static buffer to 4 KB, so the
  `array local … gets STATIC storage` and `large static data` build warnings are gone.
- **`anukulana_version()` `10104` → `10200`.** The `smoke.tcyr` assertion moves with it.

### Fixed

- **The in-tree build compiles again.** At 1.1.4 the `path` overrides pulled the 6.7.x sibling
  checkouts, which do not compile on 6.6.20. Under git first, `make build` and `make test` in the
  tree compile the tags CI compiles.

### Notes

- Builds print `./lib/ shadows version-pinned …/versions/6.7.9/lib — … sigil 3.13.15 (pinned:
  3.13.11)`. The 6.7.9 toolchain ships its own sigil from before 3.13.12. `lib/` holds the declared
  `[deps.sigil]` tag, which is what CI builds, so the `cyrius lib sync --full` the warning suggests
  isn't needed. `CYRIUS_NO_WARN_SHADOW_LIB=1` silences it.

### Verified

- **In-tree, default (git-first) mode.** On a fresh `lib/` and `cyrius.lock`, `cyrius deps` printed
  the `hint:` naming the four unused checkouts and commit-pinned all five deps: sigil `3c47656`,
  tula `3cded05`, rosnet `f065c58`, rupantara `2467829`, tyche `2c393fe`. Every vendored
  `lib/<dep>.cyr` header was confirmed at its new version. `cyrius deps --verify` reports 61
  verified and 0 failed, and `cyrius deps --locked` is clean.
- Suite **129/129** across 9 files, the same as 1.1.4. Lint has 0 `warn ` lines, fmt and vet are
  clean, and the DCE binary builds and runs.
- **Local mode.** `CYRIUS_LOCAL=1` built all four overrides from `build/local-deps/`, each reported
  against the tag CI builds. `lib/` and `cyrius.lock` were byte-identical afterwards.
- **Not run: `make fidelity` or the checkpoint demos.** The GPT-2 checkpoint is still not staged on
  the verification host, so the HF-logit gate has not been re-run at this pin or at 1.1.4's.

## [1.1.4] - 2026-11-09

A toolchain and dependency realign to the cyrius 6.6.20 set. No behavior change.

### Changed

- **Toolchain `6.6.2` → `6.6.20`.**
- **Dependencies moved to the releases built against 6.6.20.** 1.1.3 moved the toolchain but
  left all four dep tags where 1.1.2 set them.
  - `sigil` `3.12.16` → `3.13.10`. This is the sigil bundled in cyrius 6.6.20, and the last
    sigil tag pinned within 6.6.x (it pins 6.6.18; 3.13.11 moves to 6.7.5). It is also the one
    tula 1.0.3 pins.
  - `tula` `1.0.1` → `1.0.3`.
  - `rosnet` `1.1.1` → `1.1.3`. tyche comes in transitively at `1.1.1` (was `1.0.1`). Its
    `rng_normal` moves 0.011% of x86_64 draws by 1–3 ulp, and `t_randn` inherits that. The
    suite never draws: `lora_init` (the only `t_randn` caller) is reached only from the
    `gpt2-lora` / `gpt2-qlora` / `gpt2-tula` demos, whose seeded A-init can move by those ulps.
  - `rupantara` `0.4.2` → `0.4.4`. It pins rosnet `1.1.3` too, so the graph resolves a single
    rosnet.
- **`[deps].stdlib` gains `sys`.** sigil 3.13.10's `dist/sigil.deps` lists it, and tula 1.0.3
  added the same leaf. tula 1.0.3 no longer ships `dist/tula.deps`, so the manifest comment now
  points at tula's `[deps].stdlib` plus sigil's sidecar instead.
- **`src/safetensors.cyr`: `bayan_json_v_obj_get` → `bayan_json_v_obj_get_by_cstr`** (3 call
  sites: `dtype`, `shape`, `data_offsets`). bayan 1.5.10 deprecated the old name, and 6.6.20
  bundles bayan 1.5.12, so every build warned at all three sites. The old name only forwards to
  `_by_cstr`, so the lookup and its answers are the same.
- **`anukulana_version()` `10103` → `10104`.** The `smoke.tcyr` assertion moves with it.

### Verified

- **Against the tagged graph, the one CI builds.** Under 6.6.20 a `path` still shadows its
  `tag` (git-first only arrives in 6.7.6), and every `../` checkout runs ahead on a 6.7.x
  release. So the run used a copy of the tree with the four `path` lines dropped. `cyrius deps`
  commit-pinned all five deps: sigil `6d065da`, tula `ad2a39c`, rosnet `5aa4ad7`,
  rupantara `8a41767`, tyche `68bb5db`. Every vendored `lib/<dep>.cyr` header was confirmed at
  its new version.
- Suite **129/129** across 9 files, the same count as 1.1.3. Lint has 0 `warn ` lines, fmt and
  vet are clean, and the DCE binary (715,728 B) builds and runs. The only compiler warnings
  left come from inside sigil's bundle (a 256 KiB static array local) and the static-data size
  note.
- **Not run: `make fidelity` or the checkpoint demos.** The GPT-2 checkpoint was not staged on
  the verification host. rupantara 0.4.4 reports no forward change, and rosnet's CPU bundle
  changed only in whitespace between 1.1.1 and 1.1.3, but the HF-logit gate itself has not
  been re-run at this pin.

### Known

- **The in-tree build fails while the `path` overrides point at 6.7.x checkouts.** With
  `../tula` at 1.6.1 (pins 6.7.18), `cyrius build` stops at `lib/tula.cyr:445:10: expected '=',
  got '{'`. CI is unaffected because it resolves the tags. Local work needs the sibling
  checkouts at the 6.6.20-era tags, or the overrides dropped, until the pin reaches 6.7.6.

## [1.1.3] - 2026-09-11

### Changed

- **Toolchain `6.5.27` → `6.6.2`.** No source change; the value form needed none.
  Build, tests, and any bench/fuzz/distlib target the repo ships re-verified at the new pin.


## [1.1.2] — 2026-08-18

### Changed

- **Cyrius pin `6.3.31` -> `6.5.27`** (2026-08-17, ecosystem-wide ML/AI-arc realign ahead of
  the arc reopening). `cyrius lib sync --full` re-vendored the whole version-matched stdlib
  snapshot.
- **`src/safetensors.cyr`: `bayan_json_v_parse_str` -> `bayan_json_v_parse_buf`** (same
  `(buf, len)` signature; the header comment updated to match). The rename is deliberate
  upstream in bayan 1.3.0: while the cstr+len form held the `_str` name, Cyrius's
  `X(a, ...)` -> `X_str` overload dispatch silently rewrote every
  `bayan_json_v_parse(someStr)` in the ecosystem into a 1-arg call to a 2-arg function, which
  returned 0 for valid JSON. anukūlana's call site passes a raw `buf + 8`, so it was never hit
  by that bug — but the symbol it named is gone.

### Fixed

- **The suite was `0 passed / 9 failed` at the old pin — every file a compile error — and the
  bump plus the one rename above is what made it green (9/9, 129 assertions).** Two distinct
  stale-vendored-stdlib faults were stacked: `thread_local_alloc` (stdlib v6.4.65, already
  called by the vendored `sigil`) was missing outright, and once `lib sync --full` supplied it
  the newly-vendored bayan 1.4.1 exposed the `_str` -> `_buf` rename. Nothing else in
  anukūlana's source moved; the GPT-2 safetensors import path — which could not be built at
  all in this state — is compiling and green again.

### Changed

- **Dependency set brought current: `sigil` 3.9.9 -> 3.12.9, `tula` 1.0.0 -> 1.0.1,
  `rosnet` 0.2.0 -> 1.1.1, `rupantara` 0.4.0 -> 0.4.2.** All four were pinned behind releases that
  had already shipped, and all four are declared with a `path` override — so local dev and the
  129-assertion suite had been resolving the *working copies* while the declared tags went
  untested, and CI would have been the first thing to ever build the declared graph
  ([[reference_path_override_disables_the_tag_as_a_test]]). anukūlana sits last in the release
  order (it consumes tula, rosnet and rupantara), so this could only be done once those three were
  published. Verified each bump took rather than merely built — every vendored `lib/<dep>.cyr`
  header confirmed at the new version.

## [1.1.1] — 2026-07-05

**Operator-key signing (`--sk`) — ifran Lane 2 closes.** The persistence path
can now sign as a REAL operator instead of the ephemeral demo key, closing the
control-plane trust chain end-to-end.

### Added
- **`gpt2-tula … [--sk <operator.sk>]`** — optional flag: sign the NF4
  checkpoint + adapter with a 64 B seed||pk secret-key file (exactly ifran's
  `keys init` layout at `~/.ifran/operator.sk`); verification inside the
  round-trip uses the embedded public key (`sk+32`). Default (no flag) stays
  the ephemeral demo keypair — behavior unchanged.
- **`anuk_sk_load(path)`** (`src/nf4_store.cyr`) — the key-file loader:
  returns the 64 B sk, or 0 on absent/short files. Key management stays the
  caller's per tula's charter — this just lets the caller BE the operator.
- **Tests** (`tests/tcyr/nf4_store.tcyr` 13→21, suite 121→**129**) — keyfile
  round-trip bit-identity, embedded-pk consistency vs `ed25519_keypair`,
  absent/short-file rejects, sign-with-loaded-key + verify via `sk+32`,
  different-key still rejected.

### Proof (end-to-end with ifran 2.0.0)
`ifran keys init` (fresh operator key) → `gpt2-tula --sk .ifran/operator.sk`
on the real 124M checkpoint (round-trip PASS, task 8/8) → `ifran store add`
records **`verified`** for both artifacts (63.8 MB ckpt + 3.3 MB adapter;
previously `signed-unknown-key`) → `ifran store verify` — hash ok, structure
ok, **sig verified**.

## [1.1.0] — 2026-07-05

**GGUF import — the named post-1.0 headline lands** (additive 1.x minor).

### Added
- **GGUF import** (the second foreign source).
  - **`src/gguf.cyr`** — sovereign GGUF v2/v3 parser (llama.cpp's format):
    typed-KV metadata walk (all 13 value types skipped structurally — unknown
    *keys* never break the walk; unknown *type ids* hard-reject), ne-order
    tensor infos (dims[0] innermost), `general.alignment` handling (power-of-two
    8–65536, default 32), F32/F16 payloads widened through the same IEEE-754
    wideners the safetensors path uses (quantized GGML block types reject
    cleanly — a later lane). Untrusted-input rules from the v1.0 audit applied
    from line one: wrap-safe bounds on every read, null-checked allocs,
    per-tensor extent validation, sanity caps (64k tensors/KVs, 2^30 per dim,
    2^29 elems).
  - **`src/gpt2_gguf.cyr`** — GPT-2-from-GGUF mapping (`token_embd` /
    `position_embd` / `output_norm` / `blk.N.*`): ggml stores 2D weights
    `[out, in]` row-major (llama.cpp transposes HF Conv1D on conversion), so
    the mapping transposes back to rosnet's `[in, out]` and splits the fused
    `attn_qkv`; config comes from KV metadata (`gpt2.embedding_length` etc.,
    `general.architecture` must be `gpt2`); embeddings widen straight into the
    params buffer (token_embd is 309 MB as f64 — past the alloc cap).
  - **CLI `gpt2-gguf <model.gguf>`** — import via the GGUF door + the no-oracle
    gate: **PASS on the real 124M checkpoint** (batch forward vs KV-cache
    decode: 0 logit diffs).
  - **CLI `gpt2-cross <model.safetensors> <model.gguf>`** — THE cross-format
    gate: the same checkpoint through both foreign doors must land bit-identical.
    **PASS: 123,659,520 packed params, 0 diffs; 402,056 logits, 0 diffs.**
  - **`tests/tcyr/gguf.tcyr`** (38, suite 80→**121** with the fuzz adds) — in-test GGUF writer
    (ggml orientation, f64→f32/f16 narrowing over exact-representable seeds so
    the bit-identity gates are legitimate): minimal-file KV/F32/F16/reject
    coverage + a full GPT-2 export→import round-trip (params + logits
    bit-identical).
  - **`tests/tcyr/fuzz.tcyr`** (+3) — same-cut fuzz per the audit's standing
    rule: 30k byte-mutation rounds + full truncation sweep + 5k garbage buffers
    over `gg_open`, accessor probes on every accepted reader. Zero crashes.
  - **`tests/oracle/gen_gguf.py`** — disposable-venv converter (gguf + numpy +
    safetensors, no torch) reproducing llama.cpp's GPT-2 conversion choices
    (names, `[out, in]` transposes, F32, v3, alignment 32; tied `output.weight`
    omitted); Python remains a non-dependency.

## [1.0.0] — 2026-07-04

**v1.0 — the Type-3 reference freezes.** The charter (import → run → match →
adapt → persist) shipped across 0.2.0–0.5.0; this cut closes the remaining v1.0
criteria and freezes the surface. **GGUF import is the named headline post-1.0
addition** (the second foreign source — TinyLlama-class models).

### Added
- **`docs/api.md` + `STABILITY.md`** — the frozen 1.x surface: the five gated
  CLI commands (primary) + the module functions (`st_*`, `anuk_*`, `lora_*`,
  `nf4_*`), the checkpoint/adapter tensor names, exit-code convention. Demo
  hyperparameters and `_`-internals stay out-of-freeze; additions land as 1.x
  minors.
- **`tests/tcyr/fuzz.tcyr`** (5, suite 75→**80**) — the parsers-fuzz-clean
  criterion: deterministic LCG fuzz, 30k byte-mutations + full truncation sweep
  + 5k garbage buffers over `st_open` (accessor probes on every accepted
  reader) + 3k mutated/truncated oracle-fixture files. Zero crashes; replayable
  by construction.
- **`SECURITY.md`** + **`docs/audit/2026-07-04-audit.md`** — threat model +
  the v1.0 audit: **PASS after 2 fixes** (below).
- **`docs/benchmarks.md`** — v1.0 capture (Ryzen 7 5800H): `gpt2` 3.9 s ·
  `gpt2-oracle` 7.2 s · `gpt2-lora` 13.3 s · `gpt2-qlora` 53.5 s · `gpt2-tula`
  79.5 s; artifact sizes 63.8 MB ckpt / 3.3 MB adapter; honest framing
  (correctness-first CPU reference — throughput belongs to rosnet/mabda lanes).

### Fixed (audit findings — both hostile-input DoS class in `st_open`)
- **Integer-wrap in the header bounds check**: `8 + hlen > len` overflows for
  `hlen` within 8 of i64-max → replaced with the wrap-safe `hlen > len - 8`.
- **Unchecked entry-table allocation**: a hostile header declaring millions of
  tensors drove `alloc(nobj * 112)` past the 256 MB cap to 0 → null-store
  crash; now rejected cleanly.

### v1.0 criteria — all met
✅ CLI/API frozen + documented · ✅ HF-fidelity gate · ✅ LoRA FD-gated +
QLoRA/NF4 working · ✅ parsers hardened + fuzz clean + bench · ✅ audit +
SECURITY.md · ✅ downstream example green (the five-command gated pipeline on
the real checkpoint) · ✅ CHANGELOG complete.

## [0.5.0] — 2026-07-04

**M4 tail — signed NF4 persistence via tula: the Type-3 charter is FULLY built.**
The "quantize once, ship the artifact" step: the NF4 base and the trained LoRA
adapter each serialize to a **sigil-signed `.tula` file**, and everything
round-trips **bit-identical** (quantized data is discrete — disk round-trips are
exact or broken). The real checkpoint ships as **63.8 MB signed** (vs 548 MB
foreign safetensors / 989 MB f64 in memory); the adapter as **3.3 MB**.

### Changed — the "know the ecosystem" reconciliation
- **`src/nf4.cyr` base codec now DELEGATES to tula** — the 0.4.0 cut hand-rolled
  quantize/dequant/codebook, but **tula 1.0.0 already shipped that codec** in its
  frozen v1 surface (`tula_nf4_pack`/`_unpack`/`_nearest`/`_level`, codebook as
  exact bit patterns, identical block/nibble/zero-block semantics). The
  duplicate is deleted; thin wrappers keep call sites/tests stable. What stays
  genuinely local: **double-quantization per superblock-256** (the paper's
  granularity — tula's ADR 0002 suggests whole-tensor int8 for scales, too
  coarse for a 124M checkpoint). The 8-test exactness suite passes unchanged
  over tula's codec — anukulana now gates tula's NF4 through real usage.

### Added
- **`src/nf4_store.cyr`** — `anuk_nf4_save/load` (checkpoint: `"cfg"` +
  `TULA_DT_NF4` codes + double-quantized scales as `INT8` codes + `F64`
  superblock maxes, per tula's ADR-0002 sidecar convention) and
  `anuk_adapter_save/load` (`"lora.A"/"lora.B"/"lora.meta"`). Both signed via
  `tula_builder_finish_signed`; **load VERIFIES Ed25519 and rejects unsigned /
  wrong-key / tampered files** (the trust boundary tula's format exists for).
- **`gpt2-tula <model> <ckpt.tula> <adapter.tula>`** CLI + `src/tula_demo.cyr` —
  the round-trip on the real checkpoint: save signed NF4 ckpt → load+verify →
  **dequantized base bit-identical** to the in-memory pipeline (0 diffs across
  123.6M params) + cfg reconstructs → adapter trains over the LOADED base (xent
  15.62 → 0.0000) → save adapter → reload → **recomputed adapted logits
  bit-identical, task 8/8**.
- **`tests/tcyr/nf4_store.tcyr`** (13, suite 62→**75**) — toy-scale round-trip
  bit-identity + the trust boundary: wrong pk REJECTED, tampered payload byte
  REJECTED, adapter meta round-trips.

### Notes
- Key management stays the caller's (tula's charter) — the demo uses an
  ephemeral keypair; real keys arrive with the control plane (ifran port).
- Cyrius gotcha collected: `match` is a **reserved keyword** (the compiler
  rejects it as an identifier).

## [0.4.0] — 2026-07-04

**M4 — QLoRA/NF4: the adapter fine-tunes over a 4-bit frozen base.** The
adaptation arc completes its quantization half: the ENTIRE imported GPT-2
quantizes to **NF4** (blockwise 4-bit NormalFloat + double-quantized scales) and
the SAME LoRA head adapter (unchanged `src/lora.cyr`) fine-tunes over it —
989 MB of f64 base → **~62 MB codes + ~15.5 MB scale bytes**, trainable.

### Added (M4)
- **`src/nf4.cyr`** — the sovereign NF4 codec: the 16 NormalFloat quantiles
  (bitsandbytes `create_normal_map` constants, cited), blockwise absmax
  quantization (block 64, codes packed 2-per-byte), dequant, and
  **double-quantization** of the per-block scales (symmetric-u8 per superblock
  of 256 — a documented simplification of the paper's FP8+offset; same idea,
  error ≤ 1/254 relative per scale).
- **`tests/tcyr/nf4.tcyr`** (8, suite 54→**62**) — the forward-only-codec gate:
  known-answer codes (0 / ±absmax exact), all 16 quantiles snap to themselves,
  round-trip error ≤ max-half-gap × absmax on EVERY element (the largest gap is
  the **negative** side's −1.0→−0.696 — caught by the suite when the bound was
  first written off the positive side), requant idempotence (codes + scales),
  double-quant reconstruction bound.
- **`gpt2-qlora <model.safetensors>`** CLI + `src/qlora_demo.cyr` — QLoRA
  end-to-end on the real 124M checkpoint through the FULL pipeline (quant →
  double-quant → unpack → dequant → forward → adapt): **0 NaN** anywhere;
  weight error mean 0.0098 / max 0.656; **xent over the NF4 base 15.62 →
  0.0000 (800 Adam steps); greedy argmax 0/8 → 8/8; NF4 codes checksum
  unchanged.** `anuk_frozen_features` extracted from the LoRA demo (shared).

### Findings (M4)
- **4-bit honesty at 124M scale:** the NF4 base's raw forward drifts
  substantially on the arbitrary-token probes (logits maxabs 22.7 vs f64;
  base argmax agreement 0/8; initial xent 15.6 vs the f64 base's 10.8 — a
  *peaked-but-wrong* distribution, i.e. a functioning network, not a destroyed
  one). GPT-2-small is far below the scale where the paper's near-lossless
  claims live — reported as a measured property, NOT gated; the recipe's
  actual thesis (**trainability at 4-bit memory**) is what's gated, and it
  holds: the adapter recovers the task to 8/8 over the frozen 4-bit base.

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
