#!/usr/bin/env python3
"""Generate the GGUF block-type oracle for anukulana's quantized GGUF reader (1.6.0).

One-shot, DISPOSABLE-VENV tool (gguf + numpy). The fixture it writes is committed as
test data; this script is committed for reproducibility only. Python is NEVER a
build, run, or test dependency of the sovereign binary. Same pattern as
gen_fixture.py and gen_gguf.py.

    python3 -m venv /tmp/gguf-venv
    /tmp/gguf-venv/bin/pip install gguf numpy
    /tmp/gguf-venv/bin/python gen_qblocks.py ../fixtures/gguf_qblocks_v1.gguf

Generated with gguf 0.19.0 and numpy 2.5.4.

For each of llama.cpp's legacy block types (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0) the file
holds two tensors:

    <type>.q    the type's blocks, numpy shape (4, 256): 8 blocks per row, every byte
                drawn at random, so every code and every high bit turns up, and the
                f16 scales and minimums land in every class (normal, subnormal, zero,
                infinity, NaN). The first blocks' scales are set to the edge cases
                explicitly, in case the draw misses one.
    <type>.ref  F32, numpy shape (4, 256): gguf-py's `dequantize` of those blocks,
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

TYPES = [("q4_0", Q.Q4_0), ("q4_1", Q.Q4_1), ("q5_0", Q.Q5_0), ("q5_1", Q.Q5_1), ("q8_0", Q.Q8_0)]
ROWS = 4
COLS = 256

# f16 bit patterns: +0, -0, smallest subnormal, largest subnormal, smallest normal,
# 1/32, -65504, +inf, -inf, a quiet NaN
EDGE_F16 = [0x0000, 0x8000, 0x0001, 0x03FF, 0x0400, 0x2800, 0xFBFF, 0x7C00, 0xFC00, 0x7E00]


def main(out_path: str) -> None:
    rng = np.random.default_rng(20261109)
    w = GGUFWriter(out_path, "anukulana-qblocks")
    for name, qt in TYPES:
        bsz, tsz = GGML_QUANT_SIZES[qt]
        nblk = COLS // bsz
        raw = rng.integers(0, 256, size=(ROWS, nblk * tsz), dtype=np.uint8)
        # edge-case scales (and, for the _1 types, minimums) in the first blocks
        has_min = qt in (Q.Q4_1, Q.Q5_1)
        flat = raw.reshape(ROWS * nblk, tsz)
        for i, h in enumerate(EDGE_F16):
            flat[i, 0] = h & 0xFF
            flat[i, 1] = h >> 8
            if has_min:
                g = EDGE_F16[(i + 3) % len(EDGE_F16)]
                flat[i, 2] = g & 0xFF
                flat[i, 3] = g >> 8
        raw = flat.reshape(ROWS, nblk * tsz)
        with np.errstate(all="ignore"):
            ref = dequantize(raw, qt).astype(np.float32)
        assert ref.shape == (ROWS, COLS), ref.shape
        w.add_tensor(f"{name}.q", raw, raw_dtype=qt)
        w.add_tensor(f"{name}.ref", np.ascontiguousarray(ref))
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: gen_qblocks.py <out.gguf>")
    main(sys.argv[1])
