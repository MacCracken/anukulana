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
    /tmp/gguf-venv/bin/python gen_gguf.py ~/models/gpt2 ~/models/gpt2/model-q8_0.gguf Q8_0

Replicates llama.cpp's GPT-2 conversion choices:
  * tensor names: token_embd / position_embd / output_norm /
    blk.N.{attn_norm, attn_qkv, attn_output, ffn_norm, ffn_up, ffn_down}
  * 2D Conv1D weights TRANSPOSED to ggml's [out, in] row-major (HF stores
    [in, out]); embeddings and 1D tensors as-is
  * F32 data, GGUF v3, default alignment 32
  * gpt2.attention.layer_norm_epsilon from config.json, as llama.cpp's converter
    writes it (llama.cpp's loader, llama-quantize included, requires the key)
  * output.weight is OMITTED (GPT-2 ties it to token_embd; the importer reads
    token_embd) — keeps the proof file ~120 MB leaner

An optional third argument, a block type (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0; 1.6.0),
quantizes with gguf-py's reference quantizer the tensors llama.cpp's converter
would: every 2-D `.weight` except position_embd (token_embd and the four block
weights). The norms, biases and position_embd stay F32. gguf-py quantizes only these
five types; the K-quants need llama.cpp's llama-quantize.
"""
import json
import sys

import numpy as np
from gguf import GGMLQuantizationType, GGUFWriter
from gguf.quants import quantize
from safetensors.numpy import load_file


QTYPES = ("Q4_0", "Q4_1", "Q5_0", "Q5_1", "Q8_0")


def main(model_dir: str, out_path: str, qtype: str = "") -> None:
    qt = getattr(GGMLQuantizationType, qtype) if qtype else None
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
    # llama.cpp's loader requires it (llama-quantize refuses the file without it);
    # anukulana ignores it (rupantara's LayerNorm eps is fixed)
    w.add_layer_norm_eps(cfg.get("layer_norm_epsilon", 1e-5))

    def t(name: str, arr: np.ndarray, transpose: bool = False) -> None:
        a = np.ascontiguousarray(arr.T if transpose else arr, dtype=np.float32)
        if qt is not None and a.ndim == 2 and name.endswith(".weight") and name != "position_embd.weight":
            w.add_tensor(name, quantize(a, qt), raw_dtype=qt)
        else:
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
    print(f"wrote {out_path}: C={C} NL={NL} NH={NH} F={F} ctx={CTX} {qtype or 'F32'}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] not in QTYPES):
        sys.exit(f"usage: gen_gguf.py <model_dir> <out.gguf> [{'|'.join(QTYPES)}]")
    main(*sys.argv[1:])
