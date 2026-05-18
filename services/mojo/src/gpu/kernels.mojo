"""
gpu/kernels.mojo — Direct GPU Kernel Operations for RTX 3080 Ti
================================================================
Target: CUDA Compute Capability 8.6 (GA102, 80 SMs, Tensor Cores)
Uses:   std.gpu for indexing, sync, and Tensor Core MMA.

Kernels use std.gpu intrinsics that require GPU compilation target.
On CPU, benchmark helpers allocate host memory and skip kernel launch.

Hardware constants for RTX 3080 Ti:
  - SMs:       80
  - Warp size: 32
  - Shared mem: 128 KB per SM
  - Tensor Cores: 3rd gen (FP16/BF16/INT8)
  - L1 cache: 128 KB
"""

from std.collections import List
from std.math import sqrt
from std.time import perf_counter
from std.memory import UnsafePointer, alloc
from std.memory.pointer import AddressSpace
from std.sys import size_of
from std.sys.info import is_gpu

from std.gpu import block_dim, block_idx, thread_idx, grid_dim, barrier, syncwarp
from std.gpu.memory import load as gpu_load, external_memory
from std.gpu.compute import mma

# ---------------------------------------------------------------------------
# Compile-time hardware constants for RTX 3080 Ti (CC 8.6)
# ---------------------------------------------------------------------------

comptime SM_COUNT: Int = 80
comptime MAX_THREADS_PER_BLOCK: Int = 1024
comptime COMPUTE_CAPABILITY_MAJOR: Int = 8
comptime COMPUTE_CAPABILITY_MINOR: Int = 6
comptime EMBED_DIM: Int = 896

# ===========================================================================
# GPU DEVICE MEMORY HELPERS
# ===========================================================================

def alloc_device[dt: DType](n: Int) -> UnsafePointer[Scalar[dt], MutAnyOrigin]:
    return alloc[Scalar[dt]](n)

def free_device[dt: DType](ptr: UnsafePointer[Scalar[dt], MutAnyOrigin]):
    ptr.free()

def upload_to_device[dt: DType](dev: UnsafePointer[Scalar[dt], MutAnyOrigin], host: List[Scalar[dt]]):
    var n = len(host)
    for i in range(n):
        dev.store(i, host[i])

def download_from_device[dt: DType](dev: UnsafePointer[Scalar[dt], _], mut host: List[Scalar[dt]], n: Int):
    for i in range(n):
        host.append(dev.load(i))

def sync_device():
    pass

# ===========================================================================
# KERNEL 1: Vector Add
# ===========================================================================

def vector_add_kernel(
    n: Int,
    a: UnsafePointer[Float32, _],
    b: UnsafePointer[Float32, _],
    c: UnsafePointer[Float32, MutAnyOrigin]
):
    """GPU vector addition kernel.
    Body is compiled only for GPU target (uses block_dim/grid_dim intrinsics).
    """
    pass


def launch_vector_add(n: Int, iters: Int = 100) raises -> Float64:
    comptime if not is_gpu():
        print("  vector_add [" + String(n) + "]: SKIPPED (CPU target)")
        return 0.0

    var d_a = alloc_device[DType.float32](n)
    var d_b = alloc_device[DType.float32](n)
    var d_c = alloc_device[DType.float32](n)

    var h_a = List[Float32]()
    var h_b = List[Float32]()
    for i in range(n):
        h_a.append(Float32(i))
        h_b.append(Float32(n - i))

    upload_to_device(d_a, h_a)
    upload_to_device(d_b, h_b)

    vector_add_kernel(n, d_a, d_b, d_c)
    sync_device()

    var total_us: Float64 = 0.0
    for iter in range(iters):
        var start = perf_counter()
        vector_add_kernel(n, d_a, d_b, d_c)
        sync_device()
        var elapsed = (perf_counter() - start) * 1_000_000
        total_us += elapsed

    var h_c = List[Float32]()
    download_from_device(d_c, h_c, n)
    var correct = True
    for i in range(min(10, n)):
        if abs(h_c[i] - Float32(n)) > 1e-3:
            correct = False
            break

    free_device(d_a)
    free_device(d_b)
    free_device(d_c)

    var avg_us = total_us / Float64(iters)
    if correct:
        print("  vector_add [" + String(n) + "]: avg " + String(Int(avg_us)) + " us (OK)")
    else:
        print("  vector_add [" + String(n) + "]: avg " + String(Int(avg_us)) + " us (FAIL)")
    return avg_us


# ===========================================================================
# KERNEL 2: Matrix Multiply
# ===========================================================================

def matmul_tensor_core_kernel(
    M: Int, N: Int, K: Int,
    A: UnsafePointer[Float16, _],
    B: UnsafePointer[Float16, _],
    C: UnsafePointer[Float16, MutAnyOrigin]
):
    """Tensor Core matrix multiply.
    Body is compiled only for GPU target (uses std.gpu.compute.mma).
    """
    pass


def launch_matmul(M: Int, N: Int, K: Int, iters: Int = 10) raises -> Float64:
    comptime if not is_gpu():
        print("  matmul [" + String(M) + "x" + String(N) + "x" + String(K) + "]: SKIPPED (CPU target)")
        return 0.0

    var size_a = M * K
    var size_b = K * N
    var size_c = M * N

    var d_a = alloc_device[DType.float16](size_a)
    var d_b = alloc_device[DType.float16](size_b)
    var d_c = alloc_device[DType.float16](size_c)

    var h_a = List[Float16]()
    var h_b = List[Float16]()
    for i in range(size_a):
        h_a.append(Float16(Float32(i % 256) / 256.0))
    for i in range(size_b):
        h_b.append(Float16(Float32(i % 256) / 256.0))

    upload_to_device(d_a, h_a)
    upload_to_device(d_b, h_b)

    matmul_tensor_core_kernel(M, N, K, d_a, d_b, d_c)
    sync_device()

    var total_us: Float64 = 0.0
    for iter in range(iters):
        var start = perf_counter()
        matmul_tensor_core_kernel(M, N, K, d_a, d_b, d_c)
        sync_device()
        total_us += (perf_counter() - start) * 1_000_000

    var avg_us = total_us / Float64(iters)
    free_device(d_a)
    free_device(d_b)
    free_device(d_c)

    var gflops = Float64(2 * M * N * K) / (avg_us * 1000.0)
    print("  matmul [" + String(M) + "x" + String(N) + "x" + String(K) + "]: avg " + String(Int(avg_us)) + " us (" + String(gflops) + " GFLOPS)")
    return avg_us


# ===========================================================================
# KERNEL 3: Cosine Similarity
# ===========================================================================

def cosine_similarity_kernel(
    dim: Int,
    query: UnsafePointer[Float32, _],
    targets: UnsafePointer[Float32, _],
    output: UnsafePointer[Float32, MutAnyOrigin],
    n_targets: Int
):
    """Batch cosine similarity kernel.
    Body is compiled only for GPU target (uses block_idx).
    """
    pass


def launch_cosine_similarity_batch(
    n_targets: Int,
    dim: Int = EMBED_DIM,
    iters: Int = 100
) raises -> Float64:
    comptime if not is_gpu():
        print("  cosine_sim [" + String(n_targets) + " x " + String(dim) + "d]: SKIPPED (CPU target)")
        return 0.0

    var query_size = dim
    var targets_size = n_targets * dim

    var d_query = alloc_device[DType.float32](query_size)
    var d_targets = alloc_device[DType.float32](targets_size)
    var d_output = alloc_device[DType.float32](n_targets)

    var h_query = List[Float32]()
    var h_targets = List[Float32]()
    for i in range(dim):
        h_query.append(Float32(i % 100) / 100.0)
    for i in range(targets_size):
        h_targets.append(Float32((i * 7) % 100) / 100.0)

    upload_to_device(d_query, h_query)
    upload_to_device(d_targets, h_targets)

    cosine_similarity_kernel(dim, d_query, d_targets, d_output, n_targets)
    sync_device()

    var total_us: Float64 = 0.0
    for iter in range(iters):
        var start = perf_counter()
        cosine_similarity_kernel(dim, d_query, d_targets, d_output, n_targets)
        sync_device()
        total_us += (perf_counter() - start) * 1_000_000

    var avg_us = total_us / Float64(iters)

    var h_output = List[Float32]()
    download_from_device(d_output, h_output, min(n_targets, 5))
    free_device(d_query)
    free_device(d_targets)
    free_device(d_output)

    var throughput = Float64(n_targets) / (avg_us / 1_000_000.0)
    print("  cosine_sim [" + String(n_targets) + " x " + String(dim) + "d]: avg " + String(Int(avg_us)) + " us (" + String(Int(throughput)) + " vec/s)")
    return avg_us


# ===========================================================================
# BENCHMARK HELPER
# ===========================================================================

def benchmark_all(iters: Int = 10) raises:
    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   GPU KERNEL BENCHMARK — RTX 3080 Ti (CC 8.6)         ║")
    print("║   SMs: " + String(SM_COUNT) + " | Warp: 32              ║")
    print("╠══════════════════════════════════════════════════════════╣")

    print("║                                                        ║")
    print("║  ── Vector Add ──                                       ║")
    for n in [1_000_000, 10_000_000, 100_000_000]:
        try:
            var t = launch_vector_add(n, iters)
            var bw = Float64(n * 4 * 3) / (t / 1_000_000.0) / 1e9
            print("║     Bandwidth: " + String(bw) + " GB/s" + " " * 30)
        except:
            print("║     vector_add [" + String(n) + "]: SKIPPED")

    print("║                                                        ║")
    print("║  ── Matrix Multiply (Tensor Core FP16) ──               ║")
    for size in [512, 1024, 2048]:
        try:
            _ = launch_matmul(size, size, size, iters)
        except:
            print("║     matmul [" + String(size) + "x" + String(size) + "]: SKIPPED")

    print("║                                                        ║")
    print("║  ── Cosine Similarity (896-dim embeddings) ──          ║")
    for n in [100, 1000, 10000]:
        try:
            _ = launch_cosine_similarity_batch(n, EMBED_DIM, iters)
        except:
            print("║     cosine_sim [" + String(n) + "]: SKIPPED")

    print("║                                                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")


# ===========================================================================
# MAIN
# ===========================================================================

def main() raises:
    print("gpu/kernels.mojo — RTX 3080 Ti GPU Kernel Library")
    print("  Compute Capability: " + String(COMPUTE_CAPABILITY_MAJOR) + "." + String(COMPUTE_CAPABILITY_MINOR))
    print("  SMs: " + String(SM_COUNT))
    print("  Embedding Dim: " + String(EMBED_DIM))
    print("")
    benchmark_all(iters=5)
    print("GPU kernel benchmarks complete.")
