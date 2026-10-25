"""Runs the experiment grid (every player on a team uses the same strategy)
and writes results. For teams mixing strategies, see metagame.py.

    python3 -m trust_model.experiments            # full grid
    python3 -m trust_model.experiments --games 50 # quick check

Grid: strategy x skill profile x defensive pressure x slump (on/off) x team weight.
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
TEAM_WEIGHTS = (1.0, 0.6)  # pure team game, and a Prisoner's Dilemma (see GAME_THEORY.md)
SLUMP_PLAYER = 2      # the star in the "one_star" profile
SLUMP_MISSES = 3      # forced misses at the start of the game
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
LABEL_KEYS = ("strategy", "skills", "pressure", "slump", "team_weight")


def run_cell(args):
    strategy_name, profile, pressure, slump, team_weight, games, base_seed = args
    cfg = GameConfig(
        skills=SKILL_PROFILES[profile],
        defensive_pressure=pressure,
        forced_misses={SLUMP_PLAYER: SLUMP_MISSES} if slump else {},
        team_weight=team_weight,
    )
    strategy = STRATEGIES[strategy_name]
    labels = dict(zip(LABEL_KEYS, (strategy_name, profile, pressure, slump, team_weight)))
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
    parser.add_argument("--games", type=int, default=200, help="games per cell")
    parser.add_argument("--seed", type=int, default=4457)
    parser.add_argument("--print-pressure", type=float, default=0.15,
                        help="pressure level to show in the printed table (all levels are saved)")
    args = parser.parse_args()

    cells = [
        (*combo, args.games, args.seed)
        for combo in itertools.product(STRATEGIES, SKILL_PROFILES, PRESSURES, (False, True), TEAM_WEIGHTS)
    ]
    with Pool() as pool:
        results = pool.map(run_cell, cells)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    raw = [row for cell in results for row in cell]
    fields = list(LABEL_KEYS) + ["game"]
    for row in raw:
        fields.extend(k for k in row if k not in fields)
    with open(os.path.join(RESULTS_DIR, "raw.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(raw)

    metric_keys = [k for k in fields if k not in LABEL_KEYS + ("game",)]
    summary = []
    for cell in results:
        out = {k: cell[0][k] for k in LABEL_KEYS}
        for k in metric_keys:
            m, half = mean_ci([row[k] for row in cell if k in row])
            out[k], out[k + "_ci95"] = m, half
        summary.append(out)

    # Efficiency: team points relative to the oracle team in the same conditions.
    oracle_ppp = {tuple(r[k] for k in LABEL_KEYS[1:]): r["points_per_possession"]
                  for r in summary if r["strategy"] == "oracle"}
    for r in summary:
        r["efficiency_vs_oracle"] = r["points_per_possession"] / oracle_ppp[tuple(r[k] for k in LABEL_KEYS[1:])]

    with open(os.path.join(RESULTS_DIR, "summary.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[-1]), restval="")
        writer.writeheader()
        writer.writerows(summary)

    show = ("points_per_possession", "efficiency_vs_oracle", "cooperation_rate", "gini_passes_received",
            "excluded_rate", "slump_player_pass_share")
    print(f"{args.games} games per cell. Full results in {RESULTS_DIR}/")
    print(f"Showing pressure = {args.print_pressure}\n")
    print(f"{'strategy':24}{'skills':10}{'slump':>6}{'lambda':>7}" + "".join(f"{k[:14]:>16}" for k in show))
    for row in summary:
        if row["pressure"] != args.print_pressure:
            continue
        vals = "".join(f"{row.get(k, float('nan')):>16.3f}" for k in show)
        print(f"{row['strategy']:24}{row['skills']:10}{str(row['slump']):>6}{row['team_weight']:>7}{vals}")


if __name__ == "__main__":
    main()
