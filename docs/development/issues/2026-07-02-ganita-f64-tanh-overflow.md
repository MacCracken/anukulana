# ganita `f64_tanh` overflows to NaN for large |x| (blocks real-model import)

**Status:** OPEN — surfaced by anukulana M2 bite 3 (real GPT-2-small import).
**Affected:** `ganita` (`ganita_f64_tanh`, aliased `f64_tanh`) → therefore every
GELU consumer: **rupantara** `ru_gelu_fwd`, **attn11** `gelu_fwd`, and anything
calling `f64_tanh` on a large argument. `ganita` is a v1.0 lib folded into the
Cyrius stdlib — **fix needs the maintainer's go (do not patch stdlib/ganita blind).**

## The bug

```
fn ganita_f64_tanh(x): i64 {
    var ex = f64_exp(x);
    var enx = f64_exp(f64_neg(x));
    return f64_div(f64_sub(ex, enx), f64_add(ex, enx));
}
```

For |x| > ~709, `f64_exp(x)` overflows to **+inf**, so this computes
`(inf - 0) / (inf + 0) = inf/inf = NaN` instead of **saturating to ±1**.

Confirmed empirically: `f64_tanh(400)` is finite (e^400 ≈ 5e173, in range);
`f64_tanh(1000)` is **NaN**.

## Why real GPT-2 hits it (toy models don't)

GPT-2's GELU (tanh approx, `gelu_new`) computes `tanh(c·(x + a·x³))`, c=√(2/π),
a=0.044715. The `x³` term makes the tanh argument exceed 709 once a pre-GELU
activation exceeds ~27. Real pretrained GPT-2 has **massive-activation outliers**
(specific positions/channels with activations in the 10²–10³ range — a documented
phenomenon). Bite 3's localization: the residual is clean through block 1, then
**block 2 produces NaN in exactly one position (768 = C elements)**; attention then
spreads it to all positions by block 3. The imported weights are 100% finite (0 NaN
in 123,659,520 params), and the batch forward == KV-cache decode bit-for-bit — so
the import is correct; the NaN is purely this `f64_tanh` overflow.

## Fix (recommended, in ganita)

Saturate before the exponential blows up — e.g.:
```
fn ganita_f64_tanh(x): i64 {
    if (f64_gt(x, f64_from(20)) == 1) { return f64_from(1); }        # tanh(20) ≈ 1 − 2e-18
    if (f64_lt(x, f64_from(0 - 20)) == 1) { return f64_from(0 - 1); }
    ... existing (e^x − e^-x)/(e^x + e^-x) ...
}
```
(20 is safely within f64 tanh's ULP of ±1 and far below the e^x overflow point.)
This fixes rupantara/attn11 GELU for free. A workaround-clamp inside `ru_gelu_fwd`'s
tanh argument would also work but leaves the primitive broken for other callers.

## Repro

`anukulana gpt2 <gpt2/model.safetensors>` → prints the finite-params check, the
batch==decode diff (0), and the NaN diagnostic. Model:
`huggingface.co/gpt2/resolve/main/model.safetensors`.
