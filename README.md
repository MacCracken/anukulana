# anukulana

**अनुकूलन — adaptation.**

`anukulana` is AGNOS's sovereign **Type-3 "Pre-Trained" reference** — the proof
that AGNOS is *sovereign from the metal up **and** interoperable with the world's
weights*. It imports a real pretrained checkpoint, runs its forward on **rosnet**
through **rupantara**'s transformer blocks, and adapts it (**LoRA → QLoRA/NF4**).
A Cyrius reference binary (like attn11 / tarka).

**Scope:** import + run + adapt. It **consumes** the pieces, it doesn't reinvent
them: the weight **format** is `tula`; the transformer **forward** is `rupantara`;
**tensors** are `rosnet`; the **tokenizer** is `akshara`. Foreign quantized-import
(NF4) lives here (**not** tentib, which is QAT-from-scratch).

## Status

**0.4.0 — the full adapt arc: LoRA + QLoRA over the frozen import (M3 + M4).**
The whole Type-3 charter is now built: `gpt2` imports a real **GPT-2-small
safetensors** and runs it on **rupantara** (batch == KV-decode bit-identical);
`gpt2-oracle` gates the forward against a **committed HF-reference fixture**
(argmax identical ×48, maxrel ≤ 1e-5 — torch ran once in a disposable venv,
never a dependency; `make fidelity`); `gpt2-lora` fine-tunes a **LoRA head
adapter** over the frozen base (FD-gated dA/dB via two rosnet `linear_bwd`
passes + hand-derived Adam — xent 10.79→0.0000, argmax 8/8, base bit-frozen);
and `gpt2-qlora` runs **QLoRA end-to-end**: the 124M base NF4-quantized
(blockwise-64 + double-quant scales, 989 MB → ~62 MB codes) with the same
adapter recovering the task 8/8 over the frozen 4-bit base. Remaining: NF4
checkpoints via tula's `nf4` dtype + adapter save/load — see
[`docs/development/roadmap.md`](docs/development/roadmap.md). Cyrius pin
**6.3.31**.

## Build & test

```sh
make build   # cyrius build src/main.cyr build/anukulana
make test    # tests/tcyr/*.tcyr
./build/anukulana        # prints usage
```

## The headline (M2) — ✅ DONE (0.3.0)

Import a GPT-2-small checkpoint → map onto rupantara's layout → **produce correct
logits on rosnet**, matched against the reference implementation. That moment is
the "sovereign AND interoperable" proof — **landed**: HF's greedy stream reproduced
exactly, logits within fp32 rounding. See the roadmap.

## Ecosystem

Gap #1's importer. See the AGNOS planning docs `type3-weight-import.md` +
`software-port-path.md`. Depends on `tula` (format, released 0.1.0), `rupantara`
(forward), `rosnet`, `akshara`.

## License

GPL-3.0-only.
