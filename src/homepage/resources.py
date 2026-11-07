"""Live CPU, memory and process numbers from /proc, with a rolling history for the graphs.

A `Sampler` takes a sample every `interval` seconds on a background thread (only `serve` starts it) and
keeps the last `keep` samples. Everything reads `/proc` (or `proc=` in tests); nothing goes through a shell.
"""
import os
import threading
import time
from collections import deque

CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def read_cpu(proc="/proc"):
    """(busy_ticks, total_ticks, ncpu) from the aggregate line of /proc/stat, or None."""
    try:
        with open(os.path.join(proc, "stat")) as fh:
            lines = fh.read().splitlines()
        f = [int(x) for x in lines[0].split()[1:]]
        ncpu = sum(1 for l in lines if l.startswith("cpu") and l[3:4].isdigit()) or 1
    except (OSError, ValueError, IndexError):
        return None
    idle = f[3] + (f[4] if len(f) > 4 else 0)      # idle + iowait
    total = sum(f[:8])                              # guest time is already inside user
    return total - idle, total, ncpu


def read_mem(proc="/proc"):
    """dict with total_kb, avail_kb, swap_total_kb, swap_free_kb, or {}."""
    try:
        with open(os.path.join(proc, "meminfo")) as fh:
            m = {l.split(":")[0]: int(l.split()[1]) for l in fh if ":" in l}
        return dict(total_kb=m["MemTotal"], avail_kb=m["MemAvailable"],
                    swap_total_kb=m.get("SwapTotal", 0), swap_free_kb=m.get("SwapFree", 0))
    except (OSError, KeyError, ValueError, IndexError):
        return {}


def read_procs(proc="/proc"):
    """{pid: (name, cpu_ticks, rss_bytes)} for every readable process."""
    out = {}
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
            f = rest.split()               # f[0] is the state (field 3)
            out[int(n)] = (name, int(f[11]) + int(f[12]), int(f[21]) * PAGE)
        except (OSError, ValueError, IndexError):
            continue                       # exited while we looked
    return out


class Sampler:
    def __init__(self, proc="/proc", interval=5, keep=180, top=8, clock=time.monotonic):
        self.proc, self.interval, self.top, self.clock = proc, interval, top, clock
        self.cpu, self.mem = deque(maxlen=keep), deque(maxlen=keep)
        self._lock = threading.Lock()
        self._prev_cpu = self._prev_procs = self._prev_at = None
        self._top_cpu, self._top_mem, self._mem, self._ncpu = [], [], {}, 1

    def sample(self):
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
                self.mem.append(round(100 * (mem["total_kb"] - mem["avail_kb"]) / mem["total_kb"], 1))
            rows = []
            dt = now - self._prev_at if self._prev_at is not None else 0
            for pid, (name, ticks, rss) in procs.items():
                prev = (self._prev_procs or {}).get(pid)
                pct = 0.0
                if prev and dt > 0 and prev[0] == name and ticks >= prev[1]:
                    pct = 100 * (ticks - prev[1]) / CLK_TCK / dt        # 100 = one full core, like top
                rows.append(dict(pid=pid, name=name, cpu=round(pct, 1), rss=rss))
            self._top_cpu = sorted(rows, key=lambda r: (-r["cpu"], -r["rss"]))[:self.top]
            self._top_mem = sorted(rows, key=lambda r: -r["rss"])[:self.top]
            self._prev_procs = {pid: (v[0], v[1]) for pid, v in procs.items()}
            self._prev_at = now

    def snapshot(self):
        with self._lock:
            m = self._mem
            return dict(
                interval=self.interval, ncpu=self._ncpu,
                cpu=list(self.cpu), mem=list(self.mem),
                mem_total_kb=m.get("total_kb", 0), mem_avail_kb=m.get("avail_kb", 0),
                swap_total_kb=m.get("swap_total_kb", 0), swap_free_kb=m.get("swap_free_kb", 0),
                top_cpu=list(self._top_cpu), top_mem=list(self._top_mem),
            )

    def start(self):
        self.sample()

        def loop():
            while True:
                time.sleep(self.interval)
                try:
                    self.sample()
                except Exception as ex:                 # keep sampling whatever happens
                    print("sampler: %s" % ex, flush=True)
        threading.Thread(target=loop, daemon=True, name="sampler").start()
