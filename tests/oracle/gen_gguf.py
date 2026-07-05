#!/usr/bin/env python3
"""Convert the staged GPT-2 safetensors checkpoint to GGUF for anukulana's
`gpt2-gguf` / `gpt2-cross` gates.

One-shot, DISPOSABLE-VENV tool (gguf + numpy + safetensors — no torch). Python
is NEVER a build, run, or test dependency of the sovereign binary; this script
exists so the GGUF proof file is byte-reproducible from the same checkpoint the
safetensors gates use. Same pattern as gen_fixture.py.

    python3 -m venv /tmp/gguf-venv
    /tmp/gguf-venv/bin/pip install gguf numpy safetensors
    /tmp/gguf-venv/bin/python gen_gguf.py ~/models/gpt2 ~/models/gpt2/model.gguf

Replicates llama.cpp's GPT-2 conversion choices:
  * tensor names: token_embd / position_embd / output_norm /
    blk.N.{attn_norm, attn_qkv, attn_output, ffn_norm, ffn_up, ffn_down}
  * 2D Conv1D weights TRANSPOSED to ggml's [out, in] row-major (HF stores
    [in, out]); embeddings and 1D tensors as-is
  * F32 data, GGUF v3, default alignment 32
  * output.weight is OMITTED (GPT-2 ties it to token_embd; the importer reads
    token_embd) — keeps the proof file ~120 MB leaner
"""
import json
import sys

import numpy as np
from gguf import GGUFWriter
from safetensors.numpy import load_file


def main(model_dir: str, out_path: str) -> None:
    cfg = json.load(open(f"{model_dir}/config.json"))
    C = cfg["n_embd"]
    NL = cfg["n_layer"]
    NH = cfg["n_head"]
    CTX = cfg["n_positions"]
    F = cfg.get("n_inner") or 4 * C

    st = load_file(f"{model_dir}/model.safetensors")
    # some exports carry a "transformer." prefix — normalize it away
    st = {k.removeprefix("transformer."): v for k, v in st.items()}

    w = GGUFWriter(out_path, "gpt2")
    w.add_embedding_length(C)
    w.add_block_count(NL)
    w.add_head_count(NH)
    w.add_context_length(CTX)
    w.add_feed_forward_length(F)

    def t(name: str, arr: np.ndarray, transpose: bool = False) -> None:
        a = np.ascontiguousarray(arr.T if transpose else arr, dtype=np.float32)
        w.add_tensor(name, a)

    t("token_embd.weight", st["wte.weight"])
    t("position_embd.weight", st["wpe.weight"])
    for i in range(NL):
        t(f"blk.{i}.attn_norm.weight", st[f"h.{i}.ln_1.weight"])
        t(f"blk.{i}.attn_norm.bias", st[f"h.{i}.ln_1.bias"])
        t(f"blk.{i}.attn_qkv.weight", st[f"h.{i}.attn.c_attn.weight"], transpose=True)
        t(f"blk.{i}.attn_qkv.bias", st[f"h.{i}.attn.c_attn.bias"])
        t(f"blk.{i}.attn_output.weight", st[f"h.{i}.attn.c_proj.weight"], transpose=True)
        t(f"blk.{i}.attn_output.bias", st[f"h.{i}.attn.c_proj.bias"])
        t(f"blk.{i}.ffn_norm.weight", st[f"h.{i}.ln_2.weight"])
        t(f"blk.{i}.ffn_norm.bias", st[f"h.{i}.ln_2.bias"])
        t(f"blk.{i}.ffn_up.weight", st[f"h.{i}.mlp.c_fc.weight"], transpose=True)
        t(f"blk.{i}.ffn_up.bias", st[f"h.{i}.mlp.c_fc.bias"])
        t(f"blk.{i}.ffn_down.weight", st[f"h.{i}.mlp.c_proj.weight"], transpose=True)
        t(f"blk.{i}.ffn_down.bias", st[f"h.{i}.mlp.c_proj.bias"])
    t("output_norm.weight", st["ln_f.weight"])
    t("output_norm.bias", st["ln_f.bias"])

    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    print(f"wrote {out_path}: C={C} NL={NL} NH={NH} F={F} ctx={CTX}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
