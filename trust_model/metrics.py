"""Turns a GameLog into the measures named in our research question."""
from typing import Dict, List, Optional, Sequence

from .config import GameConfig
from .environment import GameLog


def gini(values: Sequence[float]) -> float:
    """0 = perfectly even, 1 = one player gets everything."""
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if total == 0:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted) / (n * total) - (n + 1) / n


def cold_run_recoveries(log: GameLog, cfg: GameConfig) -> List[Optional[int]]:
    """For each run of `cold_run_length` straight misses, the number of
    possessions until that player next receives a pass.
    None = no pass within `recovery_window` possessions (exclusion)."""
    passes_to = {j: [] for j in range(cfg.n_players)}
    for poss, _, receiver, _ in log.passes:
        passes_to[receiver].append(poss)

    last_valid_start = cfg.possessions_per_game - 1 - cfg.recovery_window
    streak = [0] * cfg.n_players
    recoveries = []
    for poss, shooter, made, _ in log.shots:
        streak[shooter] = 0 if made else streak[shooter] + 1
        if streak[shooter] == cfg.cold_run_length and poss <= last_valid_start:
            later = [p - poss for p in passes_to[shooter] if 0 < p - poss <= cfg.recovery_window]
            recoveries.append(later[0] if later else None)
    return recoveries


def utility_by_strategy(log: GameLog) -> Dict[str, List[float]]:
    """Each strategy's players' payoffs in this game (used by the meta-game)."""
    out: Dict[str, List[float]] = {}
    for name, u in zip(log.strategies, log.utilities):
        out.setdefault(name, []).append(u)
    return out


def summarize_game(log: GameLog, cfg: GameConfig) -> Dict[str, float]:
    n = cfg.n_players
    shots = [0] * n
    received = [0] * n
    for _, shooter, _, _ in log.shots:
        shots[shooter] += 1
    for _, _, receiver, _ in log.passes:
        received[receiver] += 1

    recoveries = cold_run_recoveries(log, cfg)
    recovered = [r for r in recoveries if r is not None]
    total_passes = max(1, sum(received))
    best = max(range(n), key=lambda j: cfg.skills[j])

    # Cooperation: of the moments when passing truly was better for the team, how often the holder passed.
    chances = [passed for _, _, better, passed in log.decisions if better]

    row = {
        "points_per_possession": sum(log.possession_points) / len(log.possession_points),
        "cooperation_rate": sum(chances) / len(chances) if chances else float("nan"),
        "mean_utility": sum(log.utilities) / n,
        "passes_per_possession": len(log.passes) / len(log.possession_points),
        "gini_passes_received": gini(received),
        "gini_shots": gini(shots),
        "best_shooter_shot_share": shots[best] / max(1, sum(shots)),
        "cold_runs": len(recoveries),
        "excluded_rate":(len(recoveries) - len(recovered)) / len(recoveries) if recoveries else float("nan"),
        "mean_recovery_possessions": sum(recovered) / len(recovered) if recovered else float("nan"),
    }

    # The player we pushed into a slump on purpose (if any).
    if cfg.forced_misses:
        target = next(iter(cfg.forced_misses))
        row["slump_player_pass_share"] = received[target] / total_passes
        row["slump_player_shots"] = shots[target]
    return row
