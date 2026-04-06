"""System Metrics — Collect and track system performance metrics for N-Xyme Dashboard."""

import time
from typing import Dict, List, Any, Union

# Try to import psutil, handle gracefully if not available
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    PSUTIL_AVAILABLE = False


class SystemMetrics:
    """Collects and stores system metrics for dashboard display.

    Tracks CPU, memory, disk, and network metrics with timestamps.
    Keeps last 60 samples in history for time-series display.
    """

    def __init__(self, max_history: int = 60) -> None:
        """Initialize SystemMetrics.

        Args:
            max_history: Maximum number of samples to keep in history (default: 60).
        """
        self._max_history = max_history
        self._cpu_history: List[float] = []
        self._memory_history: List[float] = []
        self._disk_history: List[float] = []
        self._network_history: List[float] = []
        self._timestamps: List[float] = []

    def collect(self) -> Dict[str, Any]:
        """Collect all system metrics with timestamp.

        Returns:
            Dict containing all metrics with timestamp. Returns default values
            if psutil is not available.
        """
        timestamp = time.time()
        data: Dict[str, Any] = {"timestamp": timestamp}

        if not PSUTIL_AVAILABLE or psutil is None:
            data["cpu"] = 0.0
            data["memory"] = {"percent": 0.0, "total": 0, "available": 0, "used": 0}
            data["disk"] = {
                "read_bytes": 0,
                "write_bytes": 0,
                "read_count": 0,
                "write_count": 0,
            }
            data["network"] = {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
            }
            self._cpu_history.append(0.0)
            self._memory_history.append(0.0)
            self._disk_history.append(0.0)
            self._network_history.append(0.0)
            self._timestamps.append(timestamp)
            self._trim_history()
            return data

        # CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            data["cpu"] = cpu_percent
            self._cpu_history.append(cpu_percent)
        except Exception:
            data["cpu"] = 0.0
            self._cpu_history.append(0.0)

        # Memory usage
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            data["memory"] = {
                "percent": memory_percent,
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
            }
            self._memory_history.append(memory_percent)
        except Exception:
            data["memory"] = {"percent": 0.0, "total": 0, "available": 0, "used": 0}
            self._memory_history.append(0.0)

        # Disk I/O stats
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                data["disk"] = {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                }
            else:
                data["disk"] = {
                    "read_bytes": 0,
                    "write_bytes": 0,
                    "read_count": 0,
                    "write_count": 0,
                }
            self._disk_history.append(
                data["disk"]["read_bytes"] + data["disk"]["write_bytes"]
            )
        except Exception:
            data["disk"] = {
                "read_bytes": 0,
                "write_bytes": 0,
                "read_count": 0,
                "write_count": 0,
            }
            self._disk_history.append(0.0)

        # Network I/O stats
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                data["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                }
            else:
                data["network"] = {
                    "bytes_sent": 0,
                    "bytes_recv": 0,
                    "packets_sent": 0,
                    "packets_recv": 0,
                    "errin": 0,
                    "errout": 0,
                }
            self._network_history.append(
                data["network"]["bytes_recv"] + data["network"]["bytes_sent"]
            )
        except Exception:
            data["network"] = {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
            }
            self._network_history.append(0.0)

        # Store timestamp
        self._timestamps.append(timestamp)

        # Trim history to max size
        self._trim_history()

        return data

    def _trim_history(self) -> None:
        """Trim all history lists to max_history size."""
        if len(self._cpu_history) > self._max_history:
            self._cpu_history = self._cpu_history[-self._max_history :]
        if len(self._memory_history) > self._max_history:
            self._memory_history = self._memory_history[-self._max_history :]
        if len(self._disk_history) > self._max_history:
            self._disk_history = self._disk_history[-self._max_history :]
        if len(self._network_history) > self._max_history:
            self._network_history = self._network_history[-self._max_history :]
        if len(self._timestamps) > self._max_history:
            self._timestamps = self._timestamps[-self._max_history :]

    def get_cpu(self) -> float:
        """Get latest CPU usage percentage.

        Returns:
            Latest CPU usage as percentage (0.0-100.0).
        """
        return self._cpu_history[-1] if self._cpu_history else 0.0

    def get_memory(self) -> float:
        """Get latest memory usage percentage.

        Returns:
            Latest memory usage as percentage (0.0-100.0).
        """
        return self._memory_history[-1] if self._memory_history else 0.0

    def get_disk(self) -> Dict[str, int]:
        """Get latest disk I/O stats.

        Returns:
            Dict containing disk I/O statistics.
        """
        if not PSUTIL_AVAILABLE or psutil is None:
            return {
                "read_bytes": 0,
                "write_bytes": 0,
                "read_count": 0,
                "write_count": 0,
            }
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                return {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                }
        except Exception:
            pass
        return {"read_bytes": 0, "write_bytes": 0, "read_count": 0, "write_count": 0}

    def get_network(self) -> Dict[str, int]:
        """Get latest network I/O stats.

        Returns:
            Dict containing network I/O statistics.
        """
        if not PSUTIL_AVAILABLE or psutil is None:
            return {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
            }
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                return {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                }
        except Exception:
            pass
        return {
            "bytes_sent": 0,
            "bytes_recv": 0,
            "packets_sent": 0,
            "packets_recv": 0,
            "errin": 0,
            "errout": 0,
        }

    def get_history(self, seconds: int) -> Dict[str, List[Any]]:
        """Get metrics for the last N seconds.

        Args:
            seconds: Number of seconds to look back.

        Returns:
            Dict containing historical metrics for the specified time window.
        """
        if not self._timestamps:
            return {
                "cpu": [],
                "memory": [],
                "disk": [],
                "network": [],
                "timestamps": [],
            }

        current_time = time.time()
        cutoff_time = current_time - seconds

        # Find indices within the time window
        indices = [i for i, ts in enumerate(self._timestamps) if ts >= cutoff_time]

        if not indices:
            # If no data in range, return last N samples based on max history
            return {
                "cpu": self._cpu_history[-min(seconds, len(self._cpu_history)) :],
                "memory": self._memory_history[
                    -min(seconds, len(self._memory_history)) :
                ],
                "disk": self._disk_history[-min(seconds, len(self._disk_history)) :],
                "network": self._network_history[
                    -min(seconds, len(self._network_history)) :
                ],
                "timestamps": self._timestamps[-min(seconds, len(self._timestamps)) :],
            }

        return {
            "cpu": [self._cpu_history[i] for i in indices],
            "memory": [self._memory_history[i] for i in indices],
            "disk": [self._disk_history[i] for i in indices],
            "network": [self._network_history[i] for i in indices],
            "timestamps": [self._timestamps[i] for i in indices],
        }
