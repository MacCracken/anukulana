#!/usr/bin/env python3
"""Generate the GPT-2 HF-oracle fixture for anukulana's `gpt2-oracle` fidelity gate.

One-shot, DISPOSABLE-VENV tool (torch CPU + transformers + safetensors). The fixture
it writes is committed as test data; this script is committed for reproducibility
only — Python/torch is NEVER a build, run, or test dependency of the sovereign
binary. Regenerate only if the fixture format or the sequence set changes.

    python3 -m venv /tmp/oracle-venv
    /tmp/oracle-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
    /tmp/oracle-venv/bin/pip install transformers safetensors
    /tmp/oracle-venv/bin/python gen_fixture.py ~/models/gpt2 ../fixtures/gpt2_oracle_v1.bin

The token sequences are deterministic integer patterns (no tokenizer involved —
the gate isolates FORWARD fidelity, not tokenization). All sequences share one T
so the Cyrius side imports the checkpoint once (cfg T is fixed at import).

Fixture format v1 (little-endian):
    u64  magic  = bytes "ANUKFIX1"
    u64  n_seqs
    per sequence:
        u64  T
        u64  V
        u64  tokens[T]        (input ids)
        u64  hf_argmax[T]     (HF argmax at every position)
        f64  last_logits[V]   (HF logits at the final position, fp32 -> f64 widen)
"""
import struct
import sys

import torch
from transformers import GPT2LMHeadModel

V = 50257
T = 16
SEQS = [
    [(i * 137 + 11) % V for i in range(T)],   # the pattern src/main.cyr `gpt2` already uses
    [(i * 977 + 3) % V for i in range(T)],
    [(i * 4099 + 257) % V for i in range(T)],
]


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: gen_fixture.py <model_dir> <out.bin>")
    model_dir, out = sys.argv[1], sys.argv[2]
    model = GPT2LMHeadModel.from_pretrained(model_dir)
    model.eval()
    with open(out, "wb") as f:
        f.write(b"ANUKFIX1")
        f.write(struct.pack("<Q", len(SEQS)))
        for toks in SEQS:
            with torch.no_grad():
                logits = model(input_ids=torch.tensor([toks])).logits[0]  # (T, V) fp32
            am = logits.argmax(dim=-1).tolist()
            f.write(struct.pack("<Q", len(toks)))
            f.write(struct.pack("<Q", V))
            f.write(struct.pack(f"<{len(toks)}Q", *toks))
            f.write(struct.pack(f"<{len(am)}Q", *am))
            f.write(logits[-1].to(torch.float64).numpy().tobytes())
            print(f"seq T={len(toks)} argmax[-1]={am[-1]} "
                  f"last-logit range [{logits[-1].min():.3f}, {logits[-1].max():.3f}]")
    print(f"wrote {out}: {len(SEQS)} seqs, T={T}, V={V}")


if __name__ == "__main__":
    main()
