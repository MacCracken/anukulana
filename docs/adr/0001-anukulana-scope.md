# 0001 — anukulana scope: the Type-3 pretrained-import reference

**Status**: Accepted
**Date**: 2026-07-01

## Context

Gap #1 of the AGNOS ML stack (`type3-weight-import.md`) is: run someone else's
pretrained checkpoint sovereignly, and adapt it. That needs a **format** (tula),
a **transformer forward** (rupantara), **tensors** (rosnet), a **tokenizer**
(akshara) — and a reference that ties them together and proves the thing works.

## Decision

`anukulana` is that reference **binary**: **import** (read a foreign
safetensors/GGUF checkpoint, or a tula file), **run** (map tensors onto
rupantara's layout, forward on rosnet → logits), and **adapt** (LoRA → QLoRA/NF4).

In scope: the importer, the run driver, the adapters, the CLI. Out of scope
(consumed, not reinvented):
- **Weight format** → `tula`. **Transformer forward** → `rupantara`. **Tensors +
  LoRA linears** → `rosnet`. **Tokenizer** → `akshara`.
- **QAT-from-scratch ternary** → `tentib`. anukulana owns *quantize-an-imported-
  checkpoint* (NF4/QLoRA); tentib owns *train-to-integer*. Keep them distinct.
- **Serving API** → `hoosh` (anukulana produces logits/adapters; it is not a server).

## Consequences

- **Positive**: the "sovereign AND interoperable with the world's weights"
  headline becomes real and testable (a GPT-2 import → matching logits); the
  pieces stay small and independently useful.
- **Negative**: anukulana's forward path is **gated on rupantara** (its M2 needs
  rupantara's transformer forward). Foreign parsers (safetensors/GGUF) are new
  untrusted-input surface that must be hardened.
- **Neutral**: LoRA adds a small backward path (rosnet `linear_bwd` on the
  adapters) — FD-gated per the family discipline.

## Alternatives considered

- **Fold this into attn11** — rejected: attn11's charter excludes new training
  science and it stays the Transformer reference; the paradigm map makes Type-3
  its own reference.
- **Fold NF4 into tentib** — rejected: import-quant ≠ QAT-from-scratch (tentib
  ADR 0001). Different technique, different home.
