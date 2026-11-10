#!/usr/bin/env python3
"""Generate the GGUF block-type oracle for anukulana's quantized GGUF reader (1.6.0).

One-shot, DISPOSABLE-VENV tool (gguf + numpy). The fixture it writes is committed as
test data; this script is committed for reproducibility only. Python is NEVER a
build, run, or test dependency of the sovereign binary. Same pattern as
gen_fixture.py and gen_gguf.py.

    python3 -m venv /tmp/gguf-venv
    /tmp/gguf-venv/bin/pip install gguf numpy
    /tmp/gguf-venv/bin/python gen_qblocks.py ../fixtures/gguf_qblocks_v1.gguf
    /tmp/gguf-venv/bin/python gen_qblocks.py ../fixtures/gguf_kblocks_v1.gguf kquants

Generated with gguf 0.19.0 and numpy 2.5.4.

For each of llama.cpp's legacy block types (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0), or with
`kquants` (1.6.1) each K-quant (Q2_K, Q3_K, Q4_K, Q5_K, Q6_K), the file holds two
tensors:

    <type>.q    the type's blocks, numpy shape (4, 256) for the legacy types (8 blocks
                of 32 per row) or (4, 1024) for the K-quants (4 superblocks of 256
                per row). Every byte is drawn at random, so every code, sub-block
                scale and high bit turns up, and the
                f16 scales and minimums land in every class (normal, subnormal, zero,
                infinity, NaN). The first blocks' scales are set to the edge cases
                explicitly, in case the draw misses one.
    <type>.ref  F32, the same shape: gguf-py's `dequantize` of those blocks,
                an implementation independent of anukulana's decoders. ggml computes
                the same values (numpy's f32 arithmetic rounds as ggml's does).

GGUF v3, alignment 32, general.architecture = "anukulana-qblocks". The test
(tests/tcyr/gguf.tcyr) compares anukulana's f64 dequantization with the widened
reference bit for bit, a NaN matching any NaN.
"""
import sys

import numpy as np
from gguf import GGMLQuantizationType as Q
from gguf import GGUFWriter
from gguf.constants import GGML_QUANT_SIZES
from gguf.quants import dequantize

LEGACY = [("q4_0", Q.Q4_0), ("q4_1", Q.Q4_1), ("q5_0", Q.Q5_0), ("q5_1", Q.Q5_1), ("q8_0", Q.Q8_0)]
KQUANTS = [("q2_k", Q.Q2_K), ("q3_k", Q.Q3_K), ("q4_k", Q.Q4_K), ("q5_k", Q.Q5_K), ("q6_k", Q.Q6_K)]
SETS = {"legacy": (LEGACY, 256), "kquants": (KQUANTS, 1024)}
ROWS = 4
# the byte offsets of each type's f16 scale and f16 minimum (None: no minimum)
SCALE_AT = {
    Q.Q4_0: (0, None), Q.Q4_1: (0, 2), Q.Q5_0: (0, None), Q.Q5_1: (0, 2), Q.Q8_0: (0, None),
    Q.Q2_K: (80, 82), Q.Q3_K: (108, None), Q.Q4_K: (0, 2), Q.Q5_K: (0, 2), Q.Q6_K: (208, None),
}

# f16 bit patterns: +0, -0, smallest subnormal, largest subnormal, smallest normal,
# 1/32, -65504, +inf, -inf, a quiet NaN
EDGE_F16 = [0x0000, 0x8000, 0x0001, 0x03FF, 0x0400, 0x2800, 0xFBFF, 0x7C00, 0xFC00, 0x7E00]


def main(out_path: str, which: str = "legacy") -> None:
    types, cols = SETS[which]
    rng = np.random.default_rng(20261109)
    w = GGUFWriter(out_path, "anukulana-qblocks")
    for name, qt in types:
        bsz, tsz = GGML_QUANT_SIZES[qt]
        nblk = cols // bsz
        raw = rng.integers(0, 256, size=(ROWS, nblk * tsz), dtype=np.uint8)
        # edge-case scales (and minimums, for the types with one) in the first blocks
        d_at, m_at = SCALE_AT[qt]
        flat = raw.reshape(ROWS * nblk, tsz)
        for i, h in enumerate(EDGE_F16):
            flat[i, d_at] = h & 0xFF
            flat[i, d_at + 1] = h >> 8
            if m_at is not None:
                g = EDGE_F16[(i + 3) % len(EDGE_F16)]
                flat[i, m_at] = g & 0xFF
                flat[i, m_at + 1] = g >> 8
        raw = flat.reshape(ROWS, nblk * tsz)
        with np.errstate(all="ignore"):
            ref = dequantize(raw, qt).astype(np.float32)
        assert ref.shape == (ROWS, cols), ref.shape
        w.add_tensor(f"{name}.q", raw, raw_dtype=qt)
        w.add_tensor(f"{name}.ref", np.ascontiguousarray(ref))
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in SETS):
        sys.exit("usage: gen_qblocks.py <out.gguf> [legacy|kquants]")
    main(*sys.argv[1:])
