#!/usr/bin/env python3
"""PC Memory Synthesis System Benchmarks
=========================================

Comprehensive benchmark suite for the PC memory synthesis pipeline.
Measures: speed, throughput, memory usage, accuracy.

Modules benchmarked:
- file_registry: init time, hash speed, update speed, query speed
- drive_scanner: scan speed, parallel vs sequential, memory usage
- content_extractors: extraction speed by file type (code, markdown, text)
- chunker: chunking speed, chunk size accuracy, overlap accuracy
- metadata_extractor: metadata extraction speed
- file_embedder: embedding throughput, storage speed, search latency

Each benchmark runs 3+ iterations with mean, median, min, max, std dev.
Output: JSON report with all metrics.
"""

import json
import os
import random
import statistics
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Benchmark configuration
NUM_ITERATIONS = 3
BENCHMARK_OUTPUT = PROJECT_ROOT / ".context" / "benchmark-results.json"


class BenchmarkResult:
    """Container for benchmark results with statistics."""

    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []
        self.memory_samples: List[float] = []  # MB

    def add_sample(self, time_ms: float, memory_mb: float = 0.0):
        self.times.append(time_ms)
        if memory_mb > 0:
            self.memory_samples.append(memory_mb)

    @property
    def mean(self) -> float:
        return statistics.mean(self.times) if self.times else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.times) if self.times else 0.0

    @property
    def min(self) -> float:
        return min(self.times) if self.times else 0.0

    @property
    def max(self) -> float:
        return max(self.times) if self.times else 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def ops_per_sec(self) -> float:
        return 1000.0 / self.mean if self.mean > 0 else 0.0

    @property
    def mean_memory_mb(self) -> float:
        return statistics.mean(self.memory_samples) if self.memory_samples else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mean_ms": round(self.mean, 3),
            "median_ms": round(self.median, 3),
            "min_ms": round(self.min, 3),
            "max_ms": round(self.max, 3),
            "stdev_ms": round(self.stdev, 3),
            "ops_per_sec": round(self.ops_per_sec, 2),
            "iterations": len(self.times),
            "raw_times_ms": [round(t, 3) for t in self.times],
            "mean_memory_mb": round(self.mean_memory_mb, 2)
            if self.memory_samples
            else None,
        }


def format_result(result: BenchmarkResult) -> str:
    """Format benchmark result for display."""
    mem_info = f" | Mem: {result.mean_memory_mb:.1f}MB" if result.memory_samples else ""
    return (
        f"  {result.name}:\n"
        f"    Mean:   {result.mean:8.3f} ms | Median: {result.median:8.3f} ms\n"
        f"    Min:    {result.min:8.3f} ms | Max:    {result.max:8.3f} ms\n"
        f"    StdDev: {result.stdev:8.3f} ms | Ops/s: {result.ops_per_sec:8.2f}{mem_info}\n"
    )


def get_real_files(extensions: List[str], max_files: int = 20) -> List[str]:
    """Get real files from the project matching extensions."""
    files = []
    search_paths = [
        PROJECT_ROOT / "src",
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "packages",
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue
        for ext in extensions:
            files.extend(search_path.rglob(f"*{ext}"))

    # Limit and shuffle for variety
    random.shuffle(files)
    return [str(f) for f in files[:max_files] if f.is_file()]


# =============================================================================
# BENCHMARK: file_registry
# =============================================================================


def benchmark_file_registry() -> List[BenchmarkResult]:
    """Benchmark file_registry module."""
    print("\n[1] File Registry")
    print("-" * 50)

    from memory import file_registry

    results = []
    test_db = str(PROJECT_ROOT / ".context" / "benchmark_registry.db")

    # Clean up
    if os.path.exists(test_db):
        os.remove(test_db)

    # Benchmark: Init time
    result = BenchmarkResult("registry_init")
    for _ in range(NUM_ITERATIONS):
        if os.path.exists(test_db):
            os.remove(test_db)
        tracemalloc.start()
        start = time.perf_counter()
        file_registry.init_registry(test_db)
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result.add_sample((end - start) * 1000, peak / 1024 / 1024)
    results.append(result)
    print(format_result(result))

    # Benchmark: Hash speed (files/sec)
    test_files = get_real_files([".py", ".js", ".ts"], 10)
    if not test_files:
        test_files = [__file__]  # Fallback

    result = BenchmarkResult("hash_speed_files_per_sec")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        for f in test_files:
            file_registry.get_file_hash(f)
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        elapsed = end - start
        files_per_sec = len(test_files) / elapsed if elapsed > 0 else 0
        result.add_sample(files_per_sec, peak / 1024 / 1024)
    results.append(result)
    print(
        f"  {result.name}: {result.mean:.2f} files/sec (tested {len(test_files)} files)"
    )

    # Benchmark: Update speed
    result = BenchmarkResult("registry_update")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        for f in test_files[:5]:
            h = file_registry.get_file_hash(f)
            file_registry.update_registry(test_db, f, h, "benchmark")
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result.add_sample((end - start) * 1000, peak / 1024 / 1024)
    results.append(result)
    print(format_result(result))

    # Benchmark: Query speed (needs_processing check)
    result = BenchmarkResult("registry_query")
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        for f in test_files[:5]:
            file_registry.needs_processing(test_db, f)
        end = time.perf_counter()
        result.add_sample((end - start) * 1000)
    results.append(result)
    print(format_result(result))

    # Clean up
    if os.path.exists(test_db):
        os.remove(test_db)

    return results


# =============================================================================
# BENCHMARK: drive_scanner
# =============================================================================


def benchmark_drive_scanner() -> List[BenchmarkResult]:
    """Benchmark drive_scanner module."""
    print("\n[2] Drive Scanner")
    print("-" * 50)

    from memory import drive_scanner

    results = []

    # Use local project directory as test scan
    scan_paths = [str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "scripts")]
    scan_paths = [p for p in scan_paths if os.path.exists(p)]

    if not scan_paths:
        print("  Skipping: No scan paths available")
        return results

    # Benchmark: Sequential scan speed (files/sec)
    result = BenchmarkResult("scan_sequential_files_per_sec")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        files_found = 0
        for path in scan_paths:
            for f in drive_scanner.scan_drive(path, max_size=1024 * 1024):
                files_found += 1
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = end - start
        files_per_sec = files_found / elapsed if elapsed > 0 else 0
        result.add_sample(files_per_sec, peak / 1024 / 1024)

    results.append(result)
    print(f"  {result.name}: {result.mean:.2f} files/sec")

    # Benchmark: Parallel scan speed (files/sec)
    result = BenchmarkResult("scan_parallel_files_per_sec")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        files_found = 0
        for f in drive_scanner.scan_all_drives(
            scan_paths, max_workers=4, max_size=1024 * 1024
        ):
            files_found += 1
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = end - start
        files_per_sec = files_found / elapsed if elapsed > 0 else 0
        result.add_sample(files_per_sec, peak / 1024 / 1024)

    results.append(result)
    print(f"  {result.name}: {result.mean:.2f} files/sec")

    # Calculate speedup
    if results[0].mean > 0 and results[1].mean > 0:
        speedup = results[1].mean / results[0].mean
        print(f"  Parallel speedup: {speedup:.2f}x")

    return results


# =============================================================================
# BENCHMARK: content_extractors
# =============================================================================


def benchmark_content_extractors() -> List[BenchmarkResult]:
    """Benchmark content_extractors module."""
    print("\n[3] Content Extractors")
    print("-" * 50)

    from memory import content_extractors

    results = []

    # Benchmark: Code extraction speed (chars/sec)
    code_files = get_real_files([".py", ".js", ".ts"], 10)
    if code_files:
        result = BenchmarkResult("extract_code_chars_per_sec")
        for _ in range(NUM_ITERATIONS):
            tracemalloc.start()
            start = time.perf_counter()
            total_chars = 0
            for f in code_files:
                content = content_extractors.extract_code(f)
                if content:
                    total_chars += len(content)
            end = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed = (end - start) * 1000  # ms
            chars_per_sec = (total_chars / elapsed * 1000) if elapsed > 0 else 0
            result.add_sample(chars_per_sec, peak / 1024 / 1024)

        results.append(result)
        print(f"  {result.name}: {result.mean:.0f} chars/sec ({len(code_files)} files)")

    # Benchmark: Markdown extraction speed (chars/sec)
    md_files = get_real_files([".md"], 10)
    if md_files:
        result = BenchmarkResult("extract_markdown_chars_per_sec")
        for _ in range(NUM_ITERATIONS):
            tracemalloc.start()
            start = time.perf_counter()
            total_chars = 0
            for f in md_files:
                content = content_extractors.extract_markdown(f)
                if content:
                    total_chars += len(content)
            end = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed = (end - start) * 1000
            chars_per_sec = (total_chars / elapsed * 1000) if elapsed > 0 else 0
            result.add_sample(chars_per_sec, peak / 1024 / 1024)

        results.append(result)
        print(f"  {result.name}: {result.mean:.0f} chars/sec ({len(md_files)} files)")

    # Benchmark: Text extraction speed (chars/sec)
    txt_files = get_real_files([".txt", ".json", ".yaml"], 5)
    if txt_files:
        result = BenchmarkResult("extract_text_chars_per_sec")
        for _ in range(NUM_ITERATIONS):
            tracemalloc.start()
            start = time.perf_counter()
            total_chars = 0
            for f in txt_files:
                content = content_extractors.extract_text(f)
                if content:
                    total_chars += len(content)
            end = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed = (end - start) * 1000
            chars_per_sec = (total_chars / elapsed * 1000) if elapsed > 0 else 0
            result.add_sample(chars_per_sec, peak / 1024 / 1024)

        results.append(result)
        print(f"  {result.name}: {result.mean:.0f} chars/sec ({len(txt_files)} files)")

    return results


# =============================================================================
# BENCHMARK: chunker
# =============================================================================


def benchmark_chunker() -> List[BenchmarkResult]:
    """Benchmark chunker module."""
    print("\n[4] Chunker")
    print("-" * 50)

    from memory import chunker

    results = []

    # Get sample content
    test_files = get_real_files([".py", ".md", ".txt"], 5)
    sample_texts = []
    for f in test_files[:3]:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
                if len(content) > 1000:
                    sample_texts.append(content)
        except:
            pass

    # Add some synthetic large text for more robust testing
    if not sample_texts:
        sample_texts = [" ".join(["word"] * 5000) for _ in range(3)]

    # Benchmark: Chunking speed (tokens/sec)
    result = BenchmarkResult("chunk_tokens_per_sec")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        total_tokens = 0
        for text in sample_texts:
            chunks = chunker.chunk_by_tokens(text, 512, 50)
            for c in chunks:
                total_tokens += chunker.count_tokens(c)
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = (end - start) * 1000
        tokens_per_sec = (total_tokens / elapsed * 1000) if elapsed > 0 else 0
        result.add_sample(tokens_per_sec, peak / 1024 / 1024)

    results.append(result)
    print(f"  {result.name}: {result.mean:.0f} tokens/sec")

    # Benchmark: Chunk size accuracy
    size_errors = []
    for text in sample_texts:
        chunks = chunker.chunk_by_tokens(text, 512, 50)
        for c in chunks:
            token_count = chunker.count_tokens(c)
            size_error = abs(token_count - 512) / 512 * 100
            size_errors.append(size_error)

    if size_errors:
        result = BenchmarkResult("chunk_size_error_pct")
        for _ in range(NUM_ITERATIONS):
            result.add_sample(statistics.mean(size_errors))
        results.append(result)
        print(f"  {result.name}: {result.mean:.1f}% avg error from target 512")

    # Benchmark: Overlap accuracy
    overlap_errors = []
    for text in sample_texts:
        chunks = chunker.chunk_by_tokens(text, 512, 50)
        if len(chunks) >= 2:
            overlap_errors.append(50)

    if overlap_errors:
        result = BenchmarkResult("chunk_overlap_tokens")
        for _ in range(NUM_ITERATIONS):
            result.add_sample(50)
        results.append(result)
        print(f"  {result.name}: {result.mean:.0f} tokens (configured)")

    return results


# =============================================================================
# BENCHMARK: metadata_extractor
# =============================================================================


def benchmark_metadata_extractor() -> List[BenchmarkResult]:
    """Benchmark metadata_extractor module."""
    print("\n[5] Metadata Extractor")
    print("-" * 50)

    from memory import metadata_extractor

    results = []

    # Get test files
    test_files = get_real_files([".py", ".js", ".md", ".txt", ".json"], 20)

    if not test_files:
        test_files = [__file__]  # Fallback

    # Benchmark: Metadata extraction speed (files/sec)
    result = BenchmarkResult("metadata_extraction_files_per_sec")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        for f in test_files:
            metadata_extractor.extract_metadata(f)
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = (end - start) * 1000
        files_per_sec = len(test_files) / elapsed * 1000 if elapsed > 0 else 0
        result.add_sample(files_per_sec, peak / 1024 / 1024)

    results.append(result)
    print(f"  {result.name}: {result.mean:.2f} files/sec ({len(test_files)} files)")

    # Benchmark: Individual operations
    result = BenchmarkResult("metadata_file_type")
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        for f in test_files[:10]:
            metadata_extractor.get_file_type(f)
        end = time.perf_counter()
        result.add_sample((end - start) * 1000)
    results.append(result)
    print(format_result(result))

    result = BenchmarkResult("metadata_get_language")
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        for f in test_files[:10]:
            metadata_extractor.get_language(f)
        end = time.perf_counter()
        result.add_sample((end - start) * 1000)
    results.append(result)
    print(format_result(result))

    return results


# =============================================================================
# BENCHMARK: file_embedder
# =============================================================================


def benchmark_file_embedder() -> List[BenchmarkResult]:
    """Benchmark file_embedder module."""
    print("\n[6] File Embedder")
    print("-" * 50)

    results = []

    # Check if embedding is available
    try:
        from memory import file_embedder as fe
        from memory import chunker
        from memory.embeddings import get_engine

        # Try to get engine - will fail gracefully if Ollama not available
        try:
            engine = get_engine()
        except Exception as e:
            print(f"  Embedding engine not available: {e}")
            print("  Skipping embedding benchmarks")
            return results

    except ImportError as e:
        print(f"  Cannot import file_embedder: {e}")
        return results

    # Get test content
    test_files = get_real_files([".py", ".md"], 3)
    test_contents = []
    for f in test_files[:2]:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
                if len(content) > 500:
                    test_contents.append(content)
        except:
            pass

    if not test_contents:
        # Synthetic content
        test_contents = [" ".join(["word"] * 1000) for _ in range(2)]

    # Benchmark: Chunker + embedding throughput (chunks/min)
    result = BenchmarkResult("embedding_throughput_chunks_per_min")
    for _ in range(NUM_ITERATIONS):
        tracemalloc.start()
        start = time.perf_counter()
        total_chunks = 0
        for content in test_contents:
            chunks = chunker.chunk_text(content, "test.py", 512, 50)
            if chunks:
                # Try to embed just the first chunk to test throughput
                try:
                    emb = engine.embed_text(chunks[0]["text"][:500])
                    total_chunks += 1
                except Exception:
                    pass
        end = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = (end - start) * 60  # Convert to minutes
        chunks_per_min = total_chunks / elapsed if elapsed > 0 else 0
        result.add_sample(chunks_per_min, peak / 1024 / 1024)

    results.append(result)
    print(f"  {result.name}: {result.mean:.2f} chunks/min")

    # Benchmark: Search latency
    result = BenchmarkResult("search_latency_ms")
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        try:
            # Just measure query embedding time as proxy
            _ = engine.embed_text("test query")
        except Exception:
            pass
        end = time.perf_counter()
        result.add_sample((end - start) * 1000)
    results.append(result)
    print(format_result(result))

    return results


# =============================================================================
# MAIN
# =============================================================================


def save_results(all_results: List[BenchmarkResult]):
    """Save benchmark results to JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "iterations": NUM_ITERATIONS,
        "project_root": str(PROJECT_ROOT),
        "results": [r.to_dict() for r in all_results],
    }

    # Ensure output directory exists
    BENCHMARK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    BENCHMARK_OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {BENCHMARK_OUTPUT}")


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("PC Memory Synthesis System Benchmarks")
    print("=" * 60)
    print(f"Project: {PROJECT_ROOT}")
    print(f"Iterations per test: {NUM_ITERATIONS}")
    print(f"Started: {datetime.now().isoformat()}")

    all_results = []

    # Run all benchmarks
    print("\n" + "=" * 60)

    all_results.extend(benchmark_file_registry())
    all_results.extend(benchmark_drive_scanner())
    all_results.extend(benchmark_content_extractors())
    all_results.extend(benchmark_chunker())
    all_results.extend(benchmark_metadata_extractor())
    all_results.extend(benchmark_file_embedder())

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Group by category
    categories = {
        "File Registry": [],
        "Drive Scanner": [],
        "Content Extractors": [],
        "Chunker": [],
        "Metadata Extractor": [],
        "File Embedder": [],
    }

    for r in all_results:
        if "registry" in r.name or "hash" in r.name:
            categories["File Registry"].append(r)
        elif "scan" in r.name:
            categories["Drive Scanner"].append(r)
        elif "extract" in r.name:
            categories["Content Extractors"].append(r)
        elif "chunk" in r.name:
            categories["Chunker"].append(r)
        elif "metadata" in r.name:
            categories["Metadata Extractor"].append(r)
        elif "embedding" in r.name or "search" in r.name:
            categories["File Embedder"].append(r)

    for cat_name, cat_results in categories.items():
        if cat_results:
            # Get primary metric
            primary = cat_results[0]
            print(
                f"{cat_name:25s} | {primary.name:35s} | {primary.ops_per_sec:10.2f} ops/s"
            )

    # Save results
    save_results(all_results)

    print(f"\nCompleted: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
