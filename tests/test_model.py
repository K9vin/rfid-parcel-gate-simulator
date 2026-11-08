import random

import pytest

from rfidgate import HF, UHF, attempts, expected_read_rate, per_attempt_success
from rfidgate.model import attempt_read


def test_attempts_values():
    assert attempts(UHF, 1.0) == 38      # 25 reads/s * 1.5 m / 1 m/s = 37.5 -> rounds half up
    assert attempts(UHF, 3.0) == 13      # 12.5 rounds half up (same as the web demo)
    assert attempts(UHF, 2.0) == 19      # 18.75
    assert attempts(HF, 1.0) == 3
    assert attempts(HF, 3.0) == 1        # never fewer than one attempt


def test_per_attempt_success():
    assert per_attempt_success(UHF, 0) == pytest.approx(0.10)
    assert per_attempt_success(UHF, 0.2) == pytest.approx(0.10 * (1 - 0.2 * 0.85))
    assert per_attempt_success(HF, 1.0) == pytest.approx(0.55 * (1 - 0.35))


@pytest.mark.parametrize("profile", [UHF, HF])
def test_faster_parcels_are_read_less_often(profile):
    rates = [expected_read_rate(profile, v, 0.2) for v in (0.5, 1, 2, 3)]
    assert rates == sorted(rates, reverse=True)


@pytest.mark.parametrize("profile", [UHF, HF])
def test_more_interference_lowers_read_rate(profile):
    rates = [expected_read_rate(profile, 1.0, i) for i in (0, 0.2, 0.5, 0.8)]
    assert rates == sorted(rates, reverse=True)


def test_uhf_beats_hf_when_clean_but_hf_wins_under_heavy_interference():
    assert expected_read_rate(UHF, 1.0, 0.2) > expected_read_rate(HF, 1.0, 0.2)
    assert expected_read_rate(HF, 1.0, 0.8) > expected_read_rate(UHF, 1.0, 0.8)


@pytest.mark.parametrize("speed", [0, -1])
def test_bad_speed_rejected(speed):
    with pytest.raises(ValueError):
        attempts(UHF, speed)


@pytest.mark.parametrize("interference", [-0.1, 1.1])
def test_bad_interference_rejected(interference):
    with pytest.raises(ValueError):
        per_attempt_success(UHF, interference)


def test_attempt_read_reports_first_success():
    n, hit = attempt_read(UHF, 1.0, 0.0, random.Random(1))
    assert n == 38
    assert hit is None or 1 <= hit <= n
