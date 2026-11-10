#!/usr/bin/env bash
# Build llama.cpp's llama-quantize at a pinned release and quantize the staged GPT-2
# into llama.cpp's K-quant files, for anukulana's quantized GGUF gates (1.6.1).
#
# One-shot, DISPOSABLE tool, the C++ counterpart of gen_gguf.py's venv: llama.cpp is
# cloned and built inside <work_dir> at test time, and is never a build, run or test
# dependency of the sovereign binary. gguf-py quantizes only the legacy block types,
# so the K-quants need llama.cpp's own quantizer (the maintainer's call, 2026-11-09).
#
#   tests/oracle/gen_kquants.sh ~/models/gpt2 /tmp/llama-work
#
# Needs git, cmake and a C++ compiler. <model_dir> must hold model.gguf, the F32 GGUF
# that gen_gguf.py writes (with gpt2.attention.layer_norm_epsilon, which llama.cpp's
# loader requires). Writes, into <model_dir>:
#
#   model-q2_k.gguf  model-q3_k_m.gguf  model-q4_k_m.gguf  model-q5_k_m.gguf  model-q6_k.gguf
#
# llama.cpp's standard mixes, which together use all five K-quants (Q2_K .. Q6_K).
# With --oracle it also writes, into <work_dir>, <name>-ggml-f32.gguf for each of those
# and for any model-q{4_0,4_1,5_0,5_1,8_0}.gguf present: llama-quantize's
# --allow-requantize to F32, which runs ggml's own dequantize_row_* on every tensor.
# `anukulana gpt2-qgguf <name>-ggml-f32.gguf <name>.gguf` must then report 0 params
# differing and 0 logit drift: anukulana's import equals ggml's dequantization.
set -euo pipefail

LLAMA_TAG=b12242
LLAMA_COMMIT=3b4d6ab3f79651935fba1dd93732f29022a7f5f5
LLAMA_REPO=https://github.com/ggml-org/llama.cpp.git

if [ $# -lt 2 ] || [ $# -gt 3 ] || { [ $# -eq 3 ] && [ "$3" != "--oracle" ]; }; then
    echo "usage: gen_kquants.sh <model_dir> <work_dir> [--oracle]" >&2
    exit 2
fi
model_dir=$1
work=$2
oracle=${3:-}
src="$model_dir/model.gguf"
[ -f "$src" ] || { echo "gen_kquants: no $src (run gen_gguf.py first)" >&2; exit 1; }

mkdir -p "$work"
if [ ! -d "$work/llama.cpp" ]; then
    git -c advice.detachedHead=false clone -q --depth 1 --branch "$LLAMA_TAG" "$LLAMA_REPO" "$work/llama.cpp"
fi
head=$(git -C "$work/llama.cpp" rev-parse HEAD)
if [ "$head" != "$LLAMA_COMMIT" ]; then
    echo "gen_kquants: $work/llama.cpp is at $head, not $LLAMA_TAG ($LLAMA_COMMIT)" >&2
    exit 1
fi
q="$work/llama.cpp/build/bin/llama-quantize"
if [ ! -x "$q" ]; then
    cmake -S "$work/llama.cpp" -B "$work/llama.cpp/build" -DCMAKE_BUILD_TYPE=Release \
        -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF > "$work/cmake.log"
    cmake --build "$work/llama.cpp/build" --target llama-quantize -j "$(nproc)" > "$work/build.log"
fi
echo "llama-quantize: llama.cpp $LLAMA_TAG ($LLAMA_COMMIT)"

for ft in Q2_K Q3_K_M Q4_K_M Q5_K_M Q6_K; do
    out="$model_dir/model-$(echo "$ft" | tr 'A-Z' 'a-z').gguf"
    "$q" "$src" "$out" "$ft" > "$work/quantize-$ft.log" 2>&1
    echo "wrote $out ($ft)"
done

if [ "$oracle" = "--oracle" ]; then
    for f in "$model_dir"/model-q*.gguf; do
        base=$(basename "$f" .gguf)
        "$q" --allow-requantize "$f" "$work/$base-ggml-f32.gguf" F32 > "$work/dequant-$base.log" 2>&1
        echo "wrote $work/$base-ggml-f32.gguf (ggml's dequantization of $base)"
    done
fi
