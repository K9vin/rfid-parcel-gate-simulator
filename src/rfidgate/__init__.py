"""RFID parcel gate simulator."""
from .model import HF, PROFILES, UHF, ReaderProfile, attempts, expected_read_rate, per_attempt_success
from .simulate import BatchResult, Gate, Parcel, ScanEvent, run_batch, sweep

__all__ = [
    "HF", "UHF", "PROFILES", "ReaderProfile", "attempts", "expected_read_rate",
    "per_attempt_success", "BatchResult", "Gate", "Parcel", "ScanEvent", "run_batch", "sweep",
]
__version__ = "0.1.0"
