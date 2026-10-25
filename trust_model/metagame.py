"""Meta-game: which strategies hold up when one team mixes them?

Empirical game-theoretic analysis (see GAME_THEORY.md, layer 3):
  1. Every way of filling 5 seats from the strategy set is a "profile"
     (126 profiles for 5 strategies). Each is simulated for many games, with
     strategies shuffled across seats so no strategy is tied to a skill level.
  2. The average payoff of each strategy in each profile fills a payoff table.
  3. From the table: which "everyone plays s" profiles are Nash equilibria,
     and where replicator dynamics (strategies that earn more spread) end up.

    python3 -m trust_model.metagame
    python3 -m trust_model.metagame --team-weights 1.0 0.8 0.6 0.4 --games 200
"""
import argparse
import csv
import itertools
import math
import os
import random
import statistics
from collections import Counter
from multiprocessing import Pool

from .config import META_STRATEGIES, SKILL_PROFILES, STRATEGIES, GameConfig
from .environment import Game
from .metrics import utility_by_strategy

N_SEATS = 5
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run_profile(args):
    """Simulate one profile (a sorted tuple of strategy indices). Returns
    payoff per possession for each strategy present: (mean, standard error)."""
    profile, team_weight, skills, pressure, games, base_seed = args
    cfg = GameConfig(skills=SKILL_PROFILES[skills], defensive_pressure=pressure, team_weight=team_weight)
    utilities = {s: [] for s in set(profile)}
    team_ppp = []
    for g in range(games):
        seats = list(profile)
        random.Random(base_seed * 7919 + g).shuffle(seats)
        names = [META_STRATEGIES[s] for s in seats]
        log = Game(cfg, [STRATEGIES[n] for n in names], seed=base_seed + g).play()
        per_poss = cfg.possessions_per_game
        for name, us in utility_by_strategy(log).items():
            utilities[META_STRATEGIES.index(name)].extend(u / per_poss for u in us)
        team_ppp.append(sum(log.possession_points) / per_poss)
    payoff = {s: (statistics.fmean(us), statistics.stdev(us) / math.sqrt(len(us))) for s, us in utilities.items()}
    return profile, payoff, statistics.fmean(team_ppp)


def fitness(table, x):
    """Expected payoff of each strategy when the other 4 teammates are drawn
    independently from population shares x."""
    k = len(x)
    f = [0.0] * k
    for others in itertools.combinations_with_replacement(range(k), N_SEATS - 1):
        counts = Counter(others)
        prob = math.factorial(N_SEATS - 1)
        for s, c in counts.items():
            prob *= x[s] ** c / math.factorial(c)
        if prob == 0:
            continue
        for s in range(k):
            profile = tuple(sorted(others + (s,)))
            f[s] += prob * table[profile][0][s][0]
    return f


def replicator(table, x, steps=3000, record_every=None):
    """Discrete replicator dynamics: a strategy's share grows in proportion to its payoff.
    Returns the final shares, or with `record_every` the path [x_0, x_every, ...]."""
    path = [x]
    for step in range(1, steps + 1):
        f = fitness(table, x)
        avg = sum(xi * fi for xi, fi in zip(x, f))
        x = [xi * fi / avg for xi, fi in zip(x, f)]
        if record_every and step % record_every == 0:
            path.append(x)
    return path if record_every else x


def build_table(pool, team_weight, skills, pressure, games, seed):
    """Simulate every profile. Returns {profile: (payoff per strategy, team points/poss)}."""
    profiles = itertools.combinations_with_replacement(range(len(META_STRATEGIES)), N_SEATS)
    jobs = [(p, team_weight, skills, pressure, games, seed) for p in profiles]
    return {p: (payoff, ppp) for p, payoff, ppp in pool.map(run_profile, jobs)}


def nash_check(table):
    """For each 'everyone plays s' profile: its payoff and the best single-player deviation.
    verdict: 'Nash' (no gain), '~Nash' (gain within 2 standard errors) or 'not Nash'."""
    k = len(META_STRATEGIES)
    rows = []
    for s in range(k):
        payoff, ppp = table[(s,) * N_SEATS]
        conform = payoff[s][0]
        gains = []
        for d in range(k):
            if d != s:
                mean, se = table[tuple(sorted((s,) * (N_SEATS - 1) + (d,)))][0][d]
                gains.append((mean - conform, se, d))
        gain, se, d = max(gains)
        rows.append({
            "strategy": META_STRATEGIES[s], "payoff": conform, "team_points": ppp,
            "best_deviation": META_STRATEGIES[d], "gain": gain, "gain_se": se,
            "verdict": "Nash" if gain <= 0 else ("~Nash" if gain < 2 * se else "not Nash"),
        })
    return rows


def starting_mixes():
    k = len(META_STRATEGIES)
    starts = [("uniform", [1 / k] * k)]
    for s in range(k):
        starts.append((f"mostly {META_STRATEGIES[s]}", [0.6 if i == s else 0.4 / (k - 1) for i in range(k)]))
    return starts


def analyse(table, team_weight):
    print(f"\n=== team_weight (lambda) = {team_weight} ===")
    rows = nash_check(table)

    print("\nHomogeneous teams (everyone plays the same strategy):")
    print(f"  {'strategy':24}{'payoff/poss':>12}{'team pts/poss':>15}")
    for r in rows:
        print(f"  {r['strategy']:24}{r['payoff']:>12.3f}{r['team_points']:>15.3f}")

    print("\nSymmetric Nash equilibrium check: can one player gain by switching strategy?")
    print("  (gain = deviator's payoff - what they'd get by conforming; '~' = within 2 standard errors)")
    for r in rows:
        print(f"  all {r['strategy']:24} best deviation: {r['best_deviation']:24} "
              f"gain {r['gain']:+.4f}  -> {r['verdict']}")

    print("\nReplicator dynamics (final population shares from different starting mixes):")
    print("  " + f"{'start':32}" + "".join(f"{n[:12]:>13}" for n in META_STRATEGIES))
    for label, x0 in starting_mixes():
        x = replicator(table, x0)
        print("  " + f"{label:32}" + "".join(f"{xi:>13.2f}" for xi in x))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-weights", type=float, nargs="+", default=[1.0, 0.6])
    parser.add_argument("--games", type=int, default=100, help="games per profile")
    parser.add_argument("--skills", default="equal", choices=list(SKILL_PROFILES))
    parser.add_argument("--pressure", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=4457)
    args = parser.parse_args()

    k = len(META_STRATEGIES)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"{math.comb(k + N_SEATS - 1, N_SEATS)} profiles x {args.games} games, "
          f"skills={args.skills}, pressure={args.pressure}")

    with Pool() as pool:
        for lam in args.team_weights:
            table = build_table(pool, lam, args.skills, args.pressure, args.games, args.seed)

            path = os.path.join(RESULTS_DIR, f"metagame_lambda_{lam}.csv")
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["profile", "team_points_per_possession"]
                                + [f"payoff_{n}" for n in META_STRATEGIES] + [f"se_{n}" for n in META_STRATEGIES])
                for p, (payoff, ppp) in table.items():
                    label = "+".join(f"{c}x{META_STRATEGIES[s]}" for s, c in sorted(Counter(p).items()))
                    writer.writerow([label, f"{ppp:.4f}"]
                                    + [f"{payoff[s][0]:.4f}" if s in payoff else "" for s in range(k)]
                                    + [f"{payoff[s][1]:.4f}" if s in payoff else "" for s in range(k)])
            analyse(table, lam)
    print(f"\nPayoff tables saved in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
