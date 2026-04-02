"""Parallel Dispatcher — run independent checks simultaneously."""
import concurrent.futures
import time

class ParallelDispatcher:
    def __init__(self, timeout=30):
        self.timeout = timeout

    def dispatch_parallel(self, checks):
        """Run multiple checks in parallel. Returns list of results."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as executor:
            futures = {}
            for check in checks:
                name = check.get("name", "unknown")
                fn = check["fn"]
                args = check.get("args", [])
                futures[executor.submit(self._run, name, fn, args)] = name
            for future in concurrent.futures.as_completed(futures, timeout=self.timeout):
                name = futures[future]
                try:
                    results.append(future.result(timeout=self.timeout))
                except concurrent.futures.TimeoutError:
                    results.append({"name": name, "status": "timeout", "duration_ms": self.timeout * 1000})
                except Exception as e:
                    results.append({"name": name, "status": "error", "message": str(e), "duration_ms": 0})
        return results

    def _run(self, name, fn, args):
        start = time.perf_counter()
        try:
            result = fn(*args)
            duration = round((time.perf_counter() - start) * 1000, 2)
            if isinstance(result, dict):
                result["name"] = result.get("name", name)
                result["duration_ms"] = duration
                result["status"] = result.get("status", "pass")
                return result
            return {"name": name, "status": "pass", "result": result, "duration_ms": duration}
        except Exception as e:
            return {"name": name, "status": "error", "message": str(e), "duration_ms": round((time.perf_counter() - start) * 1000, 2)}
