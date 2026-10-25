"""Play-by-play of one game, to see the agents' reasoning.

    python3 -m trust_model.demo
    python3 -m trust_model.demo --strategy long_memory --possessions 15
    python3 -m trust_model.demo --team-weight 0.6 --strategy hog,reciprocator,reciprocator,short_memory,short_memory
"""
import argparse

from .config import SKILL_PROFILES, STRATEGIES, GameConfig
from .environment import Game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="short_memory",
                        help="one strategy for the whole team, or five separated by commas: "
                             + ", ".join(STRATEGIES))
    parser.add_argument("--skills", default="one_star", choices=list(SKILL_PROFILES))
    parser.add_argument("--team-weight", type=float, default=1.0, help="lambda: 1 = team-first payoffs")
    parser.add_argument("--possessions", type=int, default=12)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--no-slump", action="store_true")
    args = parser.parse_args()

    names = args.strategy.split(",")
    if len(names) == 1:
        names *= 5
    unknown = [n for n in names if n not in STRATEGIES]
    if unknown or len(names) != 5:
        parser.error(f"need 1 or 5 known strategies; unknown: {unknown}")

    cfg = GameConfig(
        skills=SKILL_PROFILES[args.skills],
        possessions_per_game=args.possessions,
        forced_misses={} if args.no_slump else {2: 3},
        team_weight=args.team_weight,
    )
    game = Game(cfg, [STRATEGIES[n] for n in names], seed=args.seed)
    log = game.play()

    print(f"Team weight (lambda): {cfg.team_weight}")
    for j, (name, skill) in enumerate(zip(names, cfg.skills)):
        print(f"   P{j}: {name:24} true skill {skill}")
    if cfg.forced_misses:
        print("Player 2's first 3 shots are forced misses (induced slump).")

    current = -1
    for poss, text in log.events:
        if poss != current:
            current = poss
            print(f"\nPossession {poss + 1}  ({log.possession_points[poss]} pts)")
        print("   " + text)

    print("\nPlayer 0's view at the end:")
    print("   skill estimate (1.0 = average): "
          + "  ".join(f"P{j}: {game.agents[0].estimated_skill(j):.2f}" for j in range(cfg.n_players)))
    print("   reciprocity (1.0 = always passed when it should): "
          + "  ".join(f"P{j}: {game.agents[0].reciprocity(j):.2f}" for j in range(1, cfg.n_players)))
    print("\nPayoffs: " + "  ".join(f"P{j}: {u:.1f}" for j, u in enumerate(log.utilities)))


if __name__ == "__main__":
    main()
