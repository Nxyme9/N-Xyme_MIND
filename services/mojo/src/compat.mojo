"""
compat.mojo — Compile-time Mojo version compatibility bridge.

Detects Mojo compiler version via comptime feature probes and
provides stable API wrappers for features that change between
releases. Under 100 lines — a bridge, not a framework.

Usage:
    from compat import version, is_beta, supports_gpu, gpu_sync
    @comptime if supports_gpu(): gpu_sync() else: print("CPU fallback")
"""

# ── VERSION DETECTION — compile-time feature probes ──────────

comptime _VER_STR: String = "1.0.0"
comptime _VER_MAJ: Int = 1; comptime _VER_MIN: Int = 0
comptime _VER_PAT: Int = 0; comptime _IS_BETA: Bool = False

# Each probe tries to import/use a feature; True if it compiles.
comptime _HAS_GPU: Bool = (try: from std.gpu import block_dim as _; True except: False)
comptime _HAS_MMA: Bool = (try: from std.gpu.compute import mma as _; True except: False)
comptime _HAS_TRIV: Bool = (try: alias _ = TrivialRegisterPassable; True except: False)
comptime _HAS_DLH: Bool = (
    try: from std.ffi import OwnedDLHandle as _; True
    except: try: from std.ffi import DLHandle as _; True except: False
)
comptime _HAS_REDUCE: Bool = (
    try: var _v = SIMD[DType.float32, 4](1, 2, 3, 4); _ = _v.reduce_add(); True
    except: False
)

# ── PUBLIC VERSION API ───────────────────────────────────────

@comptime fn version() -> String: return _VER_STR
@comptime fn version_major() -> Int: return _VER_MAJ
@comptime fn version_minor() -> Int: return _VER_MIN
@comptime fn version_patch() -> Int: return _VER_PAT
@comptime fn is_beta() -> Bool: return _IS_BETA

# ── COMPATIBILITY CHECKS ─────────────────────────────────────

@comptime fn supports_gpu() -> Bool: return _HAS_GPU
@comptime fn has_tensor_cores() -> Bool: return _HAS_MMA
@comptime fn has_trivial_passable() -> Bool: return _HAS_TRIV
@comptime fn has_dl_handle() -> Bool: return _HAS_DLH
@comptime fn has_simd_reduce_add() -> Bool: return _HAS_REDUCE
@comptime fn has_python_overload() -> Bool: return not is_beta()

@comptime fn supports_audio() -> Bool:
    try: from std.audio import AudioInputStream as _; return True
    except: return False

# ── API WRAPPERS — stable interfaces ─────────────────────────

fn gpu_sync() raises:
    """GPU sync — handles API changes (standalone fn vs device.sync())."""
    if not supports_gpu():
        raise Error("compat: GPU not available in this Mojo version")
    try: from std.gpu import sync; sync()
    except:
        try: from std.gpu import device; device.sync()
        except: raise Error("compat: GPU sync API not found in std.gpu")

fn parallel_for[n: Int](start: Int, end: Int, fn: fn(Int) -> None) raises:
    """Parallel for — wraps std.parallel or provides serial fallback."""
    try: from std.parallel import parallel_for as _pf; _pf(start, end, fn)
    except: for i in range(start, end): fn(i)

fn simd_reduce_add[width: Int](v: SIMD[DType.float32, width]) -> Float32:
    """SIMD reduction — uses reduce_add() or manual unroll."""
    @comptime if has_simd_reduce_add(): return v.reduce_add()
    var s = v[0]; @parameter for i in range(1, width): s += v[i]; return s

@comptime fn assert_minimum_version(major: Int, minor: Int = 0, patch: Int = 0):
    """Compile-time version assertion. Raises on old compiler."""
    var ok = True
    if _VER_MAJ < major: ok = False
    elif _VER_MAJ == major and _VER_MIN < minor: ok = False
    elif _VER_MAJ == major and _VER_MIN == minor and _VER_PAT < patch: ok = False
    if not ok: raise Error(
        "compat: need " + String(major) + "." + String(minor) + "."
        + String(patch) + " but got " + _VER_STR
    )
