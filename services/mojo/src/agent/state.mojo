"""
Runtime state utilities for Mojo inference engine.
Provides VRAM detection and system metrics via Python interop.
"""
from std.python import Python

def check_vram_gb() -> Float64:
    try:
        var pynvml = Python.import_module("pynvml")
        pynvml.nvmlInit()
        var handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        var mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        var free_gb = Float64(py=mem_info.free) / (1024.0 * 1024.0 * 1024.0)
        pynvml.nvmlShutdown()
        return free_gb
    except:
        return -1.0

def get_cpu_count() -> Int:
    try:
        var os_mod = Python.import_module("os")
        return Int(py=os_mod.cpu_count())
    except:
        return 1

def get_gpu_info() -> String:
    try:
        var pynvml = Python.import_module("pynvml")
        pynvml.nvmlInit()
        var handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        var name = String(pynvml.nvmlDeviceGetName(handle))
        var mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        var total_gb = Float64(py=mem_info.total) / (1024.0 * 1024.0 * 1024.0)
        var free_gb = Float64(py=mem_info.free) / (1024.0 * 1024.0 * 1024.0)
        pynvml.nvmlShutdown()
        return "{" + "\"gpu_name\": \"" + name + "\", \"total_gb\": " + String(total_gb) + ", \"free_gb\": " + String(free_gb) + "}"
    except:
        return '{"error": "GPU info unavailable"}'

def main():
    print("VRAM GB: " + String(check_vram_gb()))
    print("CPU count: " + String(get_cpu_count()))
    print("GPU info: " + get_gpu_info())
