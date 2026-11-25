"""Live CPU, memory and process numbers from /proc, with a rolling history for the graphs.

A `Sampler` takes a sample every `interval` seconds on a background thread (only `serve` starts it) and
keeps the last `keep` samples. Everything reads `/proc` (or `proc=` in tests); nothing goes through a shell.
"""

import os
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from strata_python.tasks import Ticker

CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def read_cpu(proc: str = "/proc") -> tuple[int, int, int] | None:
    """(busy_ticks, total_ticks, ncpu) from the aggregate line of /proc/stat, or None."""
    try:
        with open(os.path.join(proc, "stat")) as fh:
            lines = fh.read().splitlines()
        f = [int(x) for x in lines[0].split()[1:]]
        ncpu = sum(1 for line in lines if line.startswith("cpu") and line[3:4].isdigit()) or 1
    except (OSError, ValueError, IndexError):
        return None
    idle = f[3] + (f[4] if len(f) > 4 else 0)  # idle + iowait
    total = sum(f[:8])  # guest time is already inside user
    return total - idle, total, ncpu


def read_mem(proc: str = "/proc") -> dict[str, int]:
    """dict with total_kb, avail_kb, swap_total_kb, swap_free_kb, or {}."""
    try:
        with open(os.path.join(proc, "meminfo")) as fh:
            m = {line.split(":")[0]: int(line.split()[1]) for line in fh if ":" in line}
        total, free = m["MemTotal"], m.get("MemFree", 0)
        buffers = m.get("Buffers", 0)
        cached = m.get("Cached", 0) + m.get("SReclaimable", 0)  # same split as free(1)
        return {
            "total_kb": total,
            "avail_kb": m["MemAvailable"],
            "free_kb": free,
            "buffers_kb": buffers,
            "cached_kb": cached,
            "used_kb": max(0, total - free - buffers - cached),
            "swap_total_kb": m.get("SwapTotal", 0),
            "swap_free_kb": m.get("SwapFree", 0),
        }
    except (OSError, KeyError, ValueError, IndexError):
        return {}


def read_procs(proc: str = "/proc") -> dict[int, tuple[str, int, int]]:
    """{pid: (name, cpu_ticks, rss_bytes)} for every readable process."""
    out: dict[int, tuple[str, int, int]] = {}
    try:
        names = os.listdir(proc)
    except OSError:
        return out
    for n in names:
        if not n.isdigit():
            continue
        try:
            with open(os.path.join(proc, n, "stat")) as fh:
                s = fh.read()
            # "pid (comm) state ..." and comm may hold spaces and parens: split on the last ")"
            head, _, rest = s.rpartition(")")
            name = head.partition("(")[2]
            f = rest.split()  # f[0] is the state (field 3)
            out[int(n)] = (name, int(f[11]) + int(f[12]), int(f[21]) * PAGE)
        except (OSError, ValueError, IndexError):
            continue  # exited while we looked
    return out


class Sampler:
    def __init__(
        self,
        proc: str = "/proc",
        interval: float = 5,
        keep: int = 180,
        top: int = 6,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.proc, self.interval, self.top, self.clock = proc, interval, top, clock
        self.cpu: deque[float] = deque(maxlen=keep)
        self.mem: deque[float] = deque(maxlen=keep)
        self.mem_cache: deque[float] = deque(maxlen=keep)
        self._lock = threading.Lock()
        self._prev_cpu: tuple[int, int, int] | None = None
        self._prev_procs: dict[int, tuple[str, int]] | None = None
        self._prev_at: float | None = None
        self._top_cpu: list[dict[str, Any]] = []
        self._top_mem: list[dict[str, Any]] = []
        self._mem: dict[str, int] = {}
        self._ncpu = 1
        self._ticker: Ticker | None = None

    def sample(self) -> None:
        now = self.clock()
        c = read_cpu(self.proc)
        procs = read_procs(self.proc)
        mem = read_mem(self.proc)
        with self._lock:
            if c:
                self._ncpu = c[2]
                if self._prev_cpu and c[1] > self._prev_cpu[1]:
                    self.cpu.append(round(100 * (c[0] - self._prev_cpu[0]) / (c[1] - self._prev_cpu[1]), 1))
                self._prev_cpu = c
            if mem:
                self._mem = mem
                self.mem.append(round(100 * mem["used_kb"] / mem["total_kb"], 1))  # apps: used without cache
                self.mem_cache.append(round(100 * (mem["buffers_kb"] + mem["cached_kb"]) / mem["total_kb"], 1))
            rows: list[dict[str, Any]] = []
            dt = now - self._prev_at if self._prev_at is not None else 0
            for pid, (name, ticks, rss) in procs.items():
                prev = (self._prev_procs or {}).get(pid)
                pct = 0.0
                if prev and dt > 0 and prev[0] == name and ticks >= prev[1]:
                    pct = 100 * (ticks - prev[1]) / CLK_TCK / dt  # 100 = one full core, like top
                rows.append({"pid": pid, "name": name, "cpu": round(pct, 1), "rss": rss})
            self._top_cpu = sorted(rows, key=lambda r: (-r["cpu"], -r["rss"]))[: self.top]
            self._top_mem = sorted(rows, key=lambda r: -r["rss"])[: self.top]
            self._prev_procs = {pid: (v[0], v[1]) for pid, v in procs.items()}
            self._prev_at = now

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            m = self._mem
            return {
                "interval": self.interval,
                "ncpu": self._ncpu,
                "cpu": list(self.cpu),
                "mem": list(self.mem),
                "mem_cache": list(self.mem_cache),
                "mem_total_kb": m.get("total_kb", 0),
                "mem_avail_kb": m.get("avail_kb", 0),
                "mem_used_kb": m.get("used_kb", 0),
                "mem_free_kb": m.get("free_kb", 0),
                "mem_buffers_kb": m.get("buffers_kb", 0),
                "mem_cached_kb": m.get("cached_kb", 0),
                "swap_total_kb": m.get("swap_total_kb", 0),
                "swap_free_kb": m.get("swap_free_kb", 0),
                "top_cpu": list(self._top_cpu),
                "top_mem": list(self._top_mem),
            }

    def start(self) -> None:
        """Sample now and then every `interval` seconds on a background thread. strata-python's `Ticker` keeps going
        whatever one sample raises and logs it, which the hand-written loop did with a print."""
        self.sample()  # the first reading is there before the first request
        self._ticker = Ticker(self.interval, self.sample, name="sampler")
        self._ticker.start()

    def stop(self) -> None:
        if self._ticker:
            self._ticker.stop()
