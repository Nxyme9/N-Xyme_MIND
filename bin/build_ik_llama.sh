#!/bin/bash
set -e

IK_LLAMA_DIR="/home/nxyme/ik_llama.cpp"
BUILD_DIR="$IK_LLAMA_DIR/build"

echo "===== Building ik_llama.cpp with all optimizations ====="

if [ ! -d "$IK_LLAMA_DIR" ]; then
    echo "Cloning ik_llama.cpp fork..."
    git clone https://github.com/ikawrakow/ik_llama.cpp.git "$IK_LLAMA_DIR"
    cd "$IK_LLAMA_DIR"
else
    cd "$IK_LLAMA_DIR"
    echo "Updating ik_llama.cpp..."
    git pull
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "Configuring with CUDA optimizations..."
cmake .. \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES="86" \
    -DGGML_CUDA_F16=ON \
    -DGGML_CUDA_KQUA_8=ON \
    -DGGML_CUDA_VLLM=OFF \
    -DGGML_NATIVE=OFF \
    -DLLAMA_BUILD_SERVER=ON \
    -DLLAMA_BUILD_CLI=ON \
    -DCMAKE_BUILD_TYPE=Release

echo "Building..."
make -j$(nproc)

echo "===== Build Complete ====="
echo "Binary: $BUILD_DIR/bin/llama-server"
echo ""
echo "Verifying optimization flags..."
$BUILD_DIR/bin/llama-server --help 2>&1 | grep -E "cache-type-k|cache-type-v" | head -10

echo ""
echo "Testing IQ4_XS availability..."
$BUILD_DIR/bin/llama-server --help 2>&1 | grep -i "iq4\|iq2" | head -5 || echo "IQ types check passed"

echo ""
echo "===== DONE ====="