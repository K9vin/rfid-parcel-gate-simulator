"""Gate simulation: parcels moving IN or OUT past one reader."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional

from .model import ReaderProfile, attempt_read, expected_read_rate


@dataclass(frozen=True)
class Parcel:
    id: int
    direction: str      # "IN" or "OUT"
    tag_id: str


@dataclass(frozen=True)
class ScanEvent:
    time_s: float
    parcel_id: int
    tag_id: str         # "(unread)" when the parcel was missed
    direction: str
    attempts: int
    read: bool
    read_on_attempt: Optional[int]


@dataclass
class BatchResult:
    tag: str
    speed: float
    interference: float
    parcels: int
    read: int
    missed: int
    actual_inside: int
    system_inside: int

    @property
    def read_rate(self) -> float:
        return self.read / self.parcels if self.parcels else 0.0

    @property
    def inventory_error(self) -> int:
        """How far the system's count of parcels inside is from the truth."""
        return self.system_inside - self.actual_inside


class Gate:
    """One reader at a gate. Keeps the true count and the system's count."""

    def __init__(self, profile: ReaderProfile, speed: float, interference: float,
                 rng: Optional[random.Random] = None):
        self.profile, self.speed, self.interference = profile, speed, interference
        self.rng = rng or random.Random()
        self.passed = self.read = self.missed = 0
        self.actual_inside = self.system_inside = 0

    def process(self, parcel: Parcel, time_s: float = 0.0) -> ScanEvent:
        n, hit = attempt_read(self.profile, self.speed, self.interference, self.rng)
        step = 1 if parcel.direction == "IN" else -1
        self.passed += 1
        self.actual_inside += step
        if hit is None:
            self.missed += 1
        else:
            self.read += 1
            self.system_inside += step
        return ScanEvent(time_s, parcel.id, parcel.tag_id if hit else "(unread)",
                         parcel.direction, n, hit is not None, hit)


def parcel_stream(count: int, rng: random.Random, p_in: float = 0.6) -> Iterator[Parcel]:
    for i in range(1, count + 1):
        yield Parcel(i, "IN" if rng.random() < p_in else "OUT", f"E280-{rng.randint(1000, 9999)}")


def live_events(profile: ReaderProfile, speed: float, interference: float, count: int,
                seed: Optional[int] = None, p_in: float = 0.6) -> Iterable[ScanEvent]:
    """Events for `count` parcels arriving one at a time (spacing max(0.4 s, 1/speed))."""
    rng = random.Random(seed)
    gate = Gate(profile, speed, interference, rng)
    spacing = max(0.4, 1.0 / speed)
    for k, parcel in enumerate(parcel_stream(count, rng, p_in)):
        yield gate.process(parcel, time_s=round(k * spacing, 2))


def run_batch(profile: ReaderProfile, speed: float, interference: float, parcels: int = 1000,
              seed: Optional[int] = None, p_in: float = 0.6) -> BatchResult:
    if parcels < 0:
        raise ValueError("parcels must be 0 or more")
    rng = random.Random(seed)
    gate = Gate(profile, speed, interference, rng)
    for parcel in parcel_stream(parcels, rng, p_in):
        gate.process(parcel)
    return BatchResult(profile.name, speed, interference, gate.passed, gate.read, gate.missed,
                       gate.actual_inside, gate.system_inside)


def sweep(profiles: List[ReaderProfile], parameter: str, values: List[float], *,
          speed: float = 1.0, interference: float = 0.2, parcels: int = 1000,
          seed: Optional[int] = None) -> List[BatchResult]:
    """Run one batch per (profile, value), varying `speed` or `interference`."""
    if parameter not in ("speed", "interference"):
        raise ValueError("parameter must be 'speed' or 'interference'")
    out = []
    for profile in profiles:
        for v in values:
            s, i = (v, interference) if parameter == "speed" else (speed, v)
            out.append(run_batch(profile, s, i, parcels, seed))
    return out


__all__ = ["Parcel", "ScanEvent", "BatchResult", "Gate", "run_batch", "sweep", "live_events",
           "parcel_stream", "expected_read_rate"]
