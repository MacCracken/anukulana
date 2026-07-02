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

**0.1.0 — M0 buildable scaffold** (prints usage/version; builds + 1 test green).
The importer/forward/LoRA land per [`docs/development/roadmap.md`](docs/development/roadmap.md).
Cyrius pin **6.3.27**.

## Build & test

```sh
make build   # cyrius build src/main.cyr build/anukulana
make test    # tests/tcyr/*.tcyr
./build/anukulana        # prints usage
```

## The headline (M2)

Import a GPT-2-small checkpoint → map onto rupantara's layout → **produce correct
logits on rosnet**, matched against the reference implementation. That moment is
the "sovereign AND interoperable" proof. See the roadmap.

## Ecosystem

Gap #1's importer. See the AGNOS planning docs `type3-weight-import.md` +
`software-port-path.md`. Depends on `tula` (format, released 0.1.0), `rupantara`
(forward), `rosnet`, `akshara`.

## License

GPL-3.0-only.
