"""The environment: runs possessions and records what happened.

One game = `possessions_per_game` possessions by the same five agents, so
memories carry over from possession to possession. Only our team's offense
is simulated; the opponent shows up as defensive pressure, steals and
defensive rebounds.
"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple

from .agents import Look, PlayerAgent
from .config import ZONE_WEIGHTS, ZONES, GameConfig, Strategy


@dataclass
class GameLog:
    shots: List[Tuple[int, int, bool, int]] = field(default_factory=list)   # (possession, shooter, made, points)
    passes: List[Tuple[int, int, int, bool]] = field(default_factory=list)  # (possession, passer, receiver, stolen)
    possession_points: List[int] = field(default_factory=list)
    events: List[Tuple[int, str]] = field(default_factory=list)            # (possession, description) in order


class Game:
    def __init__(self, config: GameConfig, strategy: Strategy, seed: int):
        self.cfg = config
        self.rng = random.Random(seed)
        n = config.n_players
        self.agents = [PlayerAgent(i, strategy, config.skills, self.rng) for i in range(n)]
        self.forced_left = dict(config.forced_misses)
        self.last_shot_possession = [0] * n
        self.log = GameLog()

    def play(self) -> GameLog:
        for poss in range(self.cfg.possessions_per_game):
            self.log.possession_points.append(self._play_possession(poss))
        return self.log

    # --- one possession -------------------------------------------------

    def _sample_look(self) -> Look:
        name, prob, points = self.rng.choices(ZONES, weights=ZONE_WEIGHTS)[0]
        return name, prob, points

    def _play_possession(self, poss: int) -> int:
        cfg, n = self.cfg, self.cfg.n_players
        clock = cfg.shot_clock - self.rng.uniform(*cfg.setup_time)
        holder = cfg.start_holder if cfg.start_holder is not None else self.rng.randrange(n)
        looks = {j: self._sample_look() for j in range(n)}

        while True:
            if clock <= cfg.must_shoot_below:
                action, target = "shoot", holder
            else:
                since_shot = [poss - last for last in self.last_shot_possession]
                action, target = self.agents[holder].decide(looks, cfg.turnover_prob, since_shot)

            if action == "shoot":
                made, points = self._shoot(poss, holder, looks[holder])
                if made:
                    return points
                if self.rng.random() < cfg.offensive_rebound_prob:
                    holder = self.rng.randrange(n)  # [Oldham] random offensive rebounder
                    clock = cfg.offensive_rebound_clock
                    looks = {j: self._sample_look() for j in range(n)}
                    continue
                return 0

            stolen = self.rng.random() < cfg.turnover_prob
            self.log.passes.append((poss, holder, target, stolen))
            self.log.events.append((poss, f"P{holder} -> P{target}" + ("  STOLEN" if stolen else "")))
            if stolen:
                return 0
            clock -= self.rng.uniform(*cfg.pass_time)
            # The receiver keeps the look they were passed for; everyone else's changes.
            looks = {j: looks[j] if j == target else self._sample_look() for j in range(n)}
            holder = target

    def _shoot(self, poss: int, shooter: int, look: Look) -> Tuple[bool, int]:
        _, base_prob, points = look
        expected = base_prob * (1 - self.cfg.defensive_pressure)
        if self.forced_left.get(shooter, 0) > 0:
            self.forced_left[shooter] -= 1
            made = False
        else:
            prob = min(self.cfg.max_make_prob, expected * self.cfg.skills[shooter])
            made = self.rng.random() < prob

        # Every teammate sees the shot and judges it against an average shooter's chance.
        for agent in self.agents:
            agent.observe_shot(shooter, made, expected)
        self.last_shot_possession[shooter] = poss
        self.log.shots.append((poss, shooter, made, points if made else 0))
        self.log.events.append((poss, f"P{shooter} shoots ({look[0]}): " + (f"MADE {points}" if made else "miss")))
        return made, (points if made else 0)
