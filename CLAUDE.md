# anukulana — Claude Code Instructions

## Identity

`anukulana` (अनुकूलन — *adaptation*) — AGNOS's sovereign **Type-3 "Pre-Trained"
reference** (binary): import a real pretrained checkpoint, run its forward on
rosnet via rupantara, and adapt it (LoRA → QLoRA/NF4). GPL-3.0-only.

**Scope — IS / IS NOT:**
- IS: import + run + adapt (the reference binary).
- IS NOT: the weight format (**tula**); the transformer forward (**rupantara**);
  tensors (**rosnet**); the tokenizer (**akshara**); QAT-from-scratch ternary
  (**tentib** — anukulana owns *import*-quant NF4, tentib owns *train*-to-integer).

## Structure & conventions

- **Reference binary** — `[build] entry = src/main.cyr`, no `[lib]`/distlib.
  `main()` lives ONLY in `src/main.cyr`. `src/lib.cyr` is the include chain
  (stdlib + domain modules) shared by `main.cyr` and tests.
- Stdlib includes only in `src/lib.cyr`; `src/*.cyr` domain modules flat. New
  module → `src/lib.cyr` (order). Consumed libs (tula/rupantara/rosnet/akshara)
  are wired in `cyrius.cyml [deps.*]` + included in `src/lib.cyr` at their milestone.
- **Never `cat | cycc`** — always `cyrius build`. `lib/` is a `cyrius deps`
  artifact (gitignored). `cyrius.lock` gitignored.
- Cyrius pin: the `cyrius = "X.Y.Z"` field in `cyrius.cyml` is the single source
  of truth — do not inline the number here (it drifts; check the manifest).
- **Do not bump VERSION; do not run git** — maintainer cuts releases; work
  accretes under CHANGELOG `[Unreleased]`.
- Lint gate: keep lines ≤120 chars (split long strings across multiple writes).

## Build / test

```sh
make build   # cyrius build src/main.cyr build/anukulana
make test    # cyrius test tests/tcyr/*.tcyr
```

Definition of done each bite: `make test` green · `cyrius fmt` clean · `cyrius
lint` no `warn ` (incl. line-length). Discipline (from attn11): Cyrius-native, no
BLAS/libc/autodiff; **FD-gate any new gradient** (the LoRA A,B path); the GPT-2
import is gated by a **logit-fidelity** benchmark vs the reference. See
`docs/development/roadmap.md`.
