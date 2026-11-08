import pytest

from rfidgate import HF, UHF, Gate, Parcel, expected_read_rate, run_batch, sweep
from rfidgate.cli import main


def test_simulation_matches_exact_probability():
    for profile, speed, interference in [(UHF, 1.0, 0.2), (UHF, 3.0, 0.2), (HF, 1.0, 0.5), (HF, 3.0, 0.2)]:
        r = run_batch(profile, speed, interference, parcels=20000, seed=7)
        assert r.read_rate == pytest.approx(expected_read_rate(profile, speed, interference), abs=0.01)


def test_same_seed_gives_same_result():
    assert run_batch(UHF, 1.0, 0.2, 500, seed=3) == run_batch(UHF, 1.0, 0.2, 500, seed=3)


def test_counts_add_up():
    r = run_batch(HF, 2.0, 0.3, 1000, seed=5)
    assert r.read + r.missed == r.parcels == 1000
    assert r.inventory_error == r.system_inside - r.actual_inside


def test_missed_reads_make_the_count_drift():
    class AlwaysMiss:
        def random(self):
            return 1.0
    gate = Gate(UHF, 1.0, 0.0, rng=AlwaysMiss())
    gate.process(Parcel(1, "IN", "E280-1111"))
    gate.process(Parcel(2, "IN", "E280-2222"))
    assert gate.actual_inside == 2 and gate.system_inside == 0 and gate.missed == 2


def test_in_and_out_directions_change_counts_opposite_ways():
    class AlwaysRead:
        def random(self):
            return 0.0
    gate = Gate(UHF, 1.0, 0.0, rng=AlwaysRead())
    gate.process(Parcel(1, "IN", "A"))
    gate.process(Parcel(2, "IN", "B"))
    gate.process(Parcel(3, "OUT", "C"))
    assert gate.actual_inside == gate.system_inside == 1


def test_sweep_shape_and_validation():
    out = sweep([UHF, HF], "speed", [0.5, 1, 2], parcels=100, seed=1)
    assert len(out) == 6
    with pytest.raises(ValueError):
        sweep([UHF], "colour", [1])


def test_cli_batch_and_errors(capsys):
    assert main(["batch", "--tag", "hf", "--parcels", "50", "--seed", "1"]) == 0
    assert "HF" in capsys.readouterr().out
    assert main(["batch", "--speed", "0"]) == 2
    assert "error" in capsys.readouterr().err


def test_cli_sweep_csv(tmp_path, capsys):
    path = tmp_path / "out.csv"
    assert main(["sweep", "--vary", "interference", "--parcels", "100", "--seed", "1", "--csv", str(path)]) == 0
    assert len(path.read_text().strip().splitlines()) == 1 + 2 * 4


def test_cli_live(capsys):
    assert main(["live", "--parcels", "5", "--seed", "2"]) == 0
    assert "Inside now" in capsys.readouterr().out
