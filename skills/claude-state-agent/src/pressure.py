"""Parse /proc/pressure (PSI) output and compute an overall stress level."""
from __future__ import annotations

import re
from typing import Optional

from .models import PressureInfo, StressLevel

# PSI line format: `some avg10=X.XX avg60=X.XX avg300=X.XX total=N`
_AVG10_RE = re.compile(r"avg10=([\d.]+)")


def _parse_avg10(line: str) -> float:
    m = _AVG10_RE.search(line)
    return float(m.group(1)) if m else 0.0


def parse_pressure(raw: Optional[str]) -> PressureInfo:
    """Parse the concatenated output from get_pressure(). Returns a PressureInfo with stress_level computed."""
    if not raw:
        return PressureInfo(stress_level="unknown")

    section = None
    io_some = io_full = 0.0
    cpu_some = 0.0
    mem_some = mem_full = 0.0
    load = 0.0

    for line in raw.splitlines():
        s = line.strip()
        if s in ("IO", "CPU", "MEM", "LOAD"):
            section = s
            continue
        if section == "IO":
            if s.startswith("some "):
                io_some = _parse_avg10(s)
            elif s.startswith("full "):
                io_full = _parse_avg10(s)
        elif section == "CPU":
            if s.startswith("some "):
                cpu_some = _parse_avg10(s)
        elif section == "MEM":
            if s.startswith("some "):
                mem_some = _parse_avg10(s)
            elif s.startswith("full "):
                mem_full = _parse_avg10(s)
        elif section == "LOAD":
            parts = s.split()
            if parts:
                try:
                    load = float(parts[0])
                except ValueError:
                    load = 0.0

    return PressureInfo(
        io_some_avg10=io_some,
        io_full_avg10=io_full,
        cpu_some_avg10=cpu_some,
        mem_some_avg10=mem_some,
        mem_full_avg10=mem_full,
        load_1min=load,
        stress_level=compute_stress_level(io_some, io_full, cpu_some, mem_some, mem_full),
    )


def compute_stress_level(io_some: float, io_full: float,
                          cpu_some: float, mem_some: float, mem_full: float) -> StressLevel:
    """Heuristic to color-code the machine's overall stress.

    Bands derived from production observation of the 14/05 ia incident
    (full IO=80%+ during the SSD storm, services completely dead).
    """
    # Red: catastrophic — system is effectively stalled
    if io_full > 30 or mem_full > 20:
        return "red"
    if io_some > 80 or cpu_some > 80 or mem_some > 60:
        return "red"

    # Orange: heavy contention — visible degradation
    if io_full > 10 or mem_full > 5:
        return "orange"
    if io_some > 50 or cpu_some > 50 or mem_some > 30:
        return "orange"

    # Yellow: noticeable but services OK
    if io_some > 20 or cpu_some > 20 or mem_some > 10:
        return "yellow"

    # Green: nothing to worry about
    return "green"
