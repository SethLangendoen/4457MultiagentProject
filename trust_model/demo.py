"""Play-by-play of one game, to see the agents' reasoning.

    python3 -m trust_model.demo
    python3 -m trust_model.demo --strategy long_memory --possessions 15
"""
import argparse

from .config import SKILL_PROFILES, STRATEGIES, GameConfig
from .environment import Game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="short_memory", choices=list(STRATEGIES))
    parser.add_argument("--skills", default="one_star", choices=list(SKILL_PROFILES))
    parser.add_argument("--possessions", type=int, default=12)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--no-slump", action="store_true")
    args = parser.parse_args()

    cfg = GameConfig(
        skills=SKILL_PROFILES[args.skills],
        possessions_per_game=args.possessions,
        forced_misses={} if args.no_slump else {2: 3},
    )
    game = Game(cfg, STRATEGIES[args.strategy], seed=args.seed)
    log = game.play()

    print(f"Strategy: {args.strategy}   true skills: {cfg.skills}")
    if cfg.forced_misses:
        print("Player 2's first 3 shots are forced misses (induced slump).")
    current = -1
    for poss, text in log.events:
        if poss != current:
            current = poss
            print(f"\nPossession {poss + 1}  ({log.possession_points[poss]} pts)")
        print("   " + text)

    print("\nPlayer 0's beliefs about each teammate's skill at the end (1.0 = average):")
    print("   " + "  ".join(f"P{j}: {game.agents[0].estimated_skill(j):.2f}" for j in range(cfg.n_players)))


if __name__ == "__main__":
    main()
