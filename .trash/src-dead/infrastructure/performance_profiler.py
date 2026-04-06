"""Performance Profiler — Profile code execution"""

import cProfile, io, logging, pstats, time
from typing import Dict

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    def __init__(self):
        self._profiles: Dict[str, dict] = {}

    def profile(self, func, *args, **kwargs) -> Dict:
        profiler = cProfile.Profile()
        start = time.time()
        result = profiler.runcall(func, *args, **kwargs)
        duration = time.time() - start
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats(20)
        profile_data = {
            "function": func.__name__,
            "duration": round(duration, 4),
            "stats": stream.getvalue(),
        }
        self._profiles[func.__name__] = profile_data
        return {"result": result, "profile": profile_data}

    def get_profile(self, func_name: str) -> Dict:
        return self._profiles.get(func_name, {})
