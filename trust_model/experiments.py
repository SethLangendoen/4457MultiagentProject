"""Runs the experiment grid and writes results.

    python3 -m trust_model.experiments            # full grid
    python3 -m trust_model.experiments --games 50 # quick check

Grid: strategy x skill profile x defensive pressure x slump (on/off).
Every cell uses the same game seeds, so strategies are compared on the
same sequence of random draws as far as their choices allow.
"""
import argparse
import csv
import itertools
import math
import os
import statistics
from multiprocessing import Pool

from .config import SKILL_PROFILES, STRATEGIES, GameConfig
from .environment import Game
from .metrics import summarize_game

PRESSURES = (0.0, 0.15, 0.30)
SLUMP_PLAYER = 2      # the star in the "one_star" profile
SLUMP_MISSES = 3      # forced misses at the start of the game
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run_cell(args):
    strategy_name, profile, pressure, slump, games, base_seed = args
    cfg = GameConfig(
        skills=SKILL_PROFILES[profile],
        defensive_pressure=pressure,
        forced_misses={SLUMP_PLAYER: SLUMP_MISSES} if slump else {},
    )
    strategy = STRATEGIES[strategy_name]
    labels = {"strategy": strategy_name, "skills": profile, "pressure": pressure, "slump": slump}
    rows = []
    for g in range(games):
        log = Game(cfg, strategy, seed=base_seed + g).play()
        rows.append({**labels, "game": g, **summarize_game(log, cfg)})
    return rows


def mean_ci(values):
    xs = [v for v in values if not (isinstance(v, float) and math.isnan(v))]
    if not xs:
        return float("nan"), float("nan")
    m = statistics.fmean(xs)
    half = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float("nan")
    return m, half


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=300, help="games per cell")
    parser.add_argument("--seed", type=int, default=4457)
    args = parser.parse_args()

    cells = [
        (s, p, pr, sl, args.games, args.seed)
        for s, p, pr, sl in itertools.product(STRATEGIES, SKILL_PROFILES, PRESSURES, (False, True))
    ]
    with Pool() as pool:
        results = pool.map(run_cell, cells)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    raw = [row for cell in results for row in cell]
    fields = sorted({k for row in raw for k in row}, key=lambda k: list(raw[-1]).index(k) if k in raw[-1] else 99)
    with open(os.path.join(RESULTS_DIR, "raw.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(raw)

    label_keys = ("strategy", "skills", "pressure", "slump")
    metric_keys = [k for k in fields if k not in label_keys + ("game",)]
    summary = []
    for cell in results:
        out = {k: cell[0][k] for k in label_keys}
        for k in metric_keys:
            m, half = mean_ci([row[k] for row in cell if k in row])
            out[k], out[k + "_ci95"] = m, half
        summary.append(out)
    with open(os.path.join(RESULTS_DIR, "summary.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]) + [k for k in summary[-1] if k not in summary[0]])
        writer.writeheader()
        writer.writerows(summary)

    show = ("points_per_possession", "gini_passes_received", "excluded_rate",
            "mean_recovery_possessions", "slump_player_pass_share")
    print(f"{args.games} games per cell. Full results in {RESULTS_DIR}/\n")
    print(f"{'strategy':22}{'skills':10}{'press':>6}{'slump':>6}" + "".join(f"{k[:14]:>16}" for k in show))
    for row in summary:
        vals = "".join(f"{row.get(k, float('nan')):>16.3f}" for k in show)
        print(f"{row['strategy']:22}{row['skills']:10}{row['pressure']:>6}{str(row['slump']):>6}{vals}")


if __name__ == "__main__":
    main()
