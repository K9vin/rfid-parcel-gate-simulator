"""Command-line interface: rfidgate batch | sweep | live"""
from __future__ import annotations

import argparse
import csv
import sys
from typing import List, Optional

from .model import PROFILES, expected_read_rate
from .simulate import BatchResult, live_events, run_batch, sweep


def _tags(names: List[str]):
    return [PROFILES[n] for n in names]


def _print_table(results: List[BatchResult]) -> None:
    cols = ("Tag", "Speed m/s", "Interf.", "Parcels", "Read", "Missed", "Read rate", "Expected", "Count error")
    rows = []
    for r in results:
        exp = expected_read_rate(PROFILES[r.tag.lower()], r.speed, r.interference)
        rows.append((r.tag, f"{r.speed:g}", f"{r.interference:.0%}", r.parcels, r.read, r.missed,
                     f"{r.read_rate:.1%}", f"{exp:.1%}", f"{r.inventory_error:+d}"))
    widths = [max(len(str(x)) for x in col) for col in zip(cols, *rows)]
    line = "  ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def _write_csv(path: str, results: List[BatchResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "speed_m_s", "interference", "parcels", "read", "missed",
                    "read_rate", "actual_inside", "system_inside"])
        for r in results:
            w.writerow([r.tag, r.speed, r.interference, r.parcels, r.read, r.missed,
                        round(r.read_rate, 4), r.actual_inside, r.system_inside])
    print(f"Saved {path}")


def _plot(path: str, results: List[BatchResult], parameter: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit("Plotting needs matplotlib: pip install 'rfid-parcel-gate-simulator[plot]'")
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    for tag in sorted({r.tag for r in results}):
        pts = [r for r in results if r.tag == tag]
        xs = [(r.speed if parameter == "speed" else r.interference * 100) for r in pts]
        ax.plot(xs, [r.read_rate * 100 for r in pts], marker="o", label=tag)
    ax.set_xlabel("Parcel speed (m/s)" if parameter == "speed" else "Interference (%)")
    ax.set_ylabel("Read rate (%)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    print(f"Saved {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rfidgate", description="RFID parcel gate simulator")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, many_tags=False):
        if many_tags:
            sp.add_argument("--tag", nargs="+", choices=PROFILES, default=["uhf", "hf"], help="reader type(s)")
        else:
            sp.add_argument("--tag", choices=PROFILES, default="uhf", help="reader type")
        sp.add_argument("--speed", type=float, default=1.0, help="parcel speed in m/s (default 1.0)")
        sp.add_argument("--interference", type=float, default=0.2, help="0 to 1 (default 0.2)")
        sp.add_argument("--seed", type=int, default=None, help="random seed for repeatable runs")

    b = sub.add_parser("batch", help="run one batch of parcels")
    common(b)
    b.add_argument("--parcels", type=int, default=1000)
    b.add_argument("--csv", help="save results to a CSV file")

    s = sub.add_parser("sweep", help="vary speed or interference and compare UHF with HF")
    common(s, many_tags=True)
    s.add_argument("--vary", choices=("speed", "interference"), default="speed")
    s.add_argument("--values", type=float, nargs="+", help="values to try (default depends on --vary)")
    s.add_argument("--parcels", type=int, default=1000)
    s.add_argument("--csv", help="save results to a CSV file")
    s.add_argument("--plot", help="save a read-rate chart (PNG); needs matplotlib")

    l = sub.add_parser("live", help="print a live gate log, one line per parcel")
    common(l)
    l.add_argument("--parcels", type=int, default=15)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "batch":
            res = [run_batch(PROFILES[args.tag], args.speed, args.interference, args.parcels, args.seed)]
            _print_table(res)
            if args.csv:
                _write_csv(args.csv, res)
        elif args.cmd == "sweep":
            values = args.values or ([0.5, 1, 2, 3] if args.vary == "speed" else [0, 0.2, 0.5, 0.8])
            res = sweep(_tags(args.tag), args.vary, values, speed=args.speed,
                        interference=args.interference, parcels=args.parcels, seed=args.seed)
            _print_table(res)
            if args.csv:
                _write_csv(args.csv, res)
            if args.plot:
                _plot(args.plot, res, args.vary)
        else:
            print(f"{'Time':>6}  {'Parcel':>6}  {'Tag ID':<10} {'Dir':<4} {'Tries':>5}  Result")
            actual = system = 0
            for e in live_events(PROFILES[args.tag], args.speed, args.interference, args.parcels, args.seed):
                step = 1 if e.direction == "IN" else -1
                actual += step
                system += step if e.read else 0
                print(f"{e.time_s:>5.1f}s  #{e.parcel_id:<5}  {e.tag_id:<10} {e.direction:<4} {e.attempts:>5}  "
                      f"{'Read' if e.read else 'MISSED'}")
            print(f"\nInside now: actual {actual}, system thinks {system}")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
