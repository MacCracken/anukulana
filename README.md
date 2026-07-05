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

**1.0.0 — STABLE: the Type-3 reference, frozen** ([`docs/api.md`](docs/api.md) +
[`STABILITY.md`](STABILITY.md); parsers fuzz-gated, audited —
[`SECURITY.md`](SECURITY.md); benchmarks captured). The charter (import → run →
match → adapt → persist), as built across 0.2.0–0.5.0: `gpt2` imports a real **GPT-2-small safetensors** and runs it on
**rupantara** (batch == KV-decode bit-identical); `gpt2-oracle` gates the
forward against a **committed HF-reference fixture** (argmax identical ×48,
maxrel ≤ 1e-5 — torch ran once in a disposable venv, never a dependency;
`make fidelity`); `gpt2-lora` fine-tunes a **LoRA head adapter** over the
frozen base (FD-gated dA/dB via two rosnet `linear_bwd` passes + hand-derived
Adam — argmax 8/8, base bit-frozen); `gpt2-qlora` runs **QLoRA** (the 124M base
NF4-quantized via **tula's codec** + local double-quant, adapter recovers 8/8
over the 4-bit base); and `gpt2-tula` **persists it all**: a sigil-signed
63.8 MB NF4 checkpoint + 3.3 MB adapter, both round-tripping **bit-identical**
with wrong-key/tampered files rejected. **The post-1.0 headline landed
2026-07-05: GGUF import** — a sovereign GGUF v2/v3 parser (llama.cpp's format)
plus the `blk.N.*` GPT-2 mapping; `gpt2-gguf` runs the real checkpoint through
the second foreign door, and `gpt2-cross` proves **both doors bit-identical**
(123.6M packed params / 402k logits, 0 diffs). Quantized GGML payloads and the
TinyLlama-class (llama-architecture) mapping are the next lanes; see
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
