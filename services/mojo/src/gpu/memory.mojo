"""
gpu/memory.mojo — Direct GPU memory access via Mojo 1.0.0b1 std.gpu.
No llama.cpp, no CUDA C, no Python bridge.

Target: RTX 3080 Ti (GA102, 80 SMs, CC 8.6, 12 GB GDDR6X)

Usage:
  mojo build gpu/memory.mojo -o gpu_memory
  ./gpu_memory  # runs benchmarks
"""

from std.collections import List
from std.math import sqrt
from std.time import perf_counter

from std.gpu import block_dim, block_idx, thread_idx, grid_dim, barrier, syncwarp
from std.gpu.memory import AddressSpace as GPUAddressSpace, load
from std.memory import alloc, UnsafePointer
from std.memory.pointer import AddressSpace

comptime GPU_WARP_SIZE: Int = 32

comptime SM_COUNT: Int = 80
comptime MAX_THREADS_PER_BLOCK: Int = 1024
comptime COMPUTE_CAPABILITY_MAJOR: Int = 8
comptime COMPUTE_CAPABILITY_MINOR: Int = 6


struct GPUBuffer[dt: DType]:
    """Handle to GPU-resident memory with parameterized dtype. Uses std.gpu device pointer."""

    var ptr: UnsafePointer[Scalar[Self.dt], MutAnyOrigin]
    var sz: Int
    var cap: Int

    def __init__(out self, capacity: Int):
        self.ptr = alloc[Scalar[Self.dt]](capacity)
        self.sz = 0
        self.cap = capacity

    def __del__(deinit self):
        if self.cap > 0:
            self.ptr.free()

    @always_inline
    def __getitem__(self, idx: Int) -> Scalar[Self.dt]:
        return self.ptr.load(idx)

    @always_inline
    def __setitem__(self, idx: Int, val: Scalar[Self.dt]):
        self.ptr.store(idx, val)

    def fill(mut self, val: Scalar[Self.dt]):
        for i in range(self.cap):
            self.ptr.store(i, val)

    def copy_from_host(mut self, data: List[Scalar[Self.dt]]):
        var n = min(len(data), self.cap)
        for i in range(n):
            self[i] = data[i]
        self.sz = n

    def copy_to_host(self) -> List[Scalar[Self.dt]]:
        var result = List[Scalar[Self.dt]]()
        for i in range(self.sz):
            result.append(self[i])
        return result^

    def benchmark(self, iters: Int = 100):
        var d_iters = Float64(iters)
        var start = perf_counter()
        for _ in range(iters):
            for j in range(min(1000, self.cap)):
                _ = self[j]
        var read_time = (perf_counter() - start) / d_iters * 1_000_000

        start = perf_counter()
        for _ in range(iters):
            for j in range(min(1000, self.cap)):
                self[j] = Scalar[Self.dt](0)
        var write_time = (perf_counter() - start) / d_iters * 1_000_000

        print("  Read  (1K elements):", read_time, "us")
        print("  Write (1K elements):", write_time, "us")
