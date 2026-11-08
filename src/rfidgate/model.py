"""Read model for a passive RFID gate.

While a tagged parcel is inside the reader's zone the reader keeps trying to
read it. Each attempt succeeds with some probability that falls as
interference (metal, liquids, crowding) rises. The parcel is captured if any
attempt succeeds.

All numbers below are ASSUMPTIONS chosen to show realistic trends (UHF has a
longer range but is more affected by its surroundings than HF). They are not
measurements from real hardware.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReaderProfile:
    name: str
    zone_m: float                      # length of the read zone along the lane (metres)
    reads_per_s: float                 # read attempts per second
    base_success: float                # chance one attempt succeeds with no interference
    interference_sensitivity: float    # 0..1, how strongly interference lowers that chance


UHF = ReaderProfile("UHF", zone_m=1.5, reads_per_s=25, base_success=0.10, interference_sensitivity=0.85)
HF = ReaderProfile("HF", zone_m=0.3, reads_per_s=10, base_success=0.55, interference_sensitivity=0.35)
PROFILES = {"uhf": UHF, "hf": HF}


def _check_speed(speed: float) -> None:
    if not speed > 0:
        raise ValueError("speed must be greater than 0 m/s")


def _check_interference(interference: float) -> None:
    if not 0.0 <= interference <= 1.0:
        raise ValueError("interference must be between 0 and 1")


def attempts(profile: ReaderProfile, speed: float) -> int:
    """Read attempts available while a parcel crosses the zone (at least one)."""
    _check_speed(speed)
    return max(1, math.floor(profile.reads_per_s * profile.zone_m / speed + 0.5))


def per_attempt_success(profile: ReaderProfile, interference: float) -> float:
    """Chance that a single read attempt succeeds."""
    _check_interference(interference)
    return profile.base_success * (1.0 - interference * profile.interference_sensitivity)


def expected_read_rate(profile: ReaderProfile, speed: float, interference: float) -> float:
    """Exact probability that a parcel is read: 1 - (1 - p) ** attempts."""
    n = attempts(profile, speed)
    p = per_attempt_success(profile, interference)
    return 1.0 - (1.0 - p) ** n


def attempt_read(profile: ReaderProfile, speed: float, interference: float,
                 rng: random.Random) -> tuple[int, Optional[int]]:
    """Simulate one parcel crossing the zone.

    Returns (attempts_available, attempt_that_succeeded). The second value is
    None if every attempt failed and the parcel was missed.
    """
    n = attempts(profile, speed)
    p = per_attempt_success(profile, interference)
    for k in range(1, n + 1):
        if rng.random() < p:
            return n, k
    return n, None
