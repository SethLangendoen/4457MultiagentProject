"""The environment: runs possessions and records what happened.

One game = `possessions_per_game` possessions by the same five agents, so
memories carry over from possession to possession. Only our team's offense
is simulated; the opponent shows up as defensive pressure, steals and
defensive rebounds.
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

from .agents import Look, PlayerAgent
from .config import ZONE_WEIGHTS, ZONES, GameConfig, Strategy


@dataclass
class GameLog:
    strategies: List[str] = field(default_factory=list)                    # strategy name of each player
    shots: List[Tuple[int, int, bool, int]] = field(default_factory=list)   # (possession, shooter, made, points)
    passes: List[Tuple[int, int, int, bool]] = field(default_factory=list)  # (possession, passer, receiver, stolen)
    # (possession, holder, passing was truly better for the team, holder passed)
    decisions: List[Tuple[int, int, bool, bool]] = field(default_factory=list)
    possession_points: List[int] = field(default_factory=list)
    own_points: List[int] = field(default_factory=list)                    # points scored by each player
    assisted_points: List[int] = field(default_factory=list)               # points scored off each player's passes
    utilities: List[float] = field(default_factory=list)                   # each player's payoff for the game
    events: List[Tuple[int, str]] = field(default_factory=list)            # (possession, description) in order
    # Only filled when Game(trace=True): per possession, its actions and a
    # snapshot of every agent's beliefs afterwards (used by the visualiser).
    timeline: List[dict] = field(default_factory=list)


class Game:
    def __init__(self, config: GameConfig, strategies: Union[Strategy, Sequence[Strategy]], seed: int,
                 trace: bool = False):
        self.cfg = config
        self.trace = trace
        self._actions: List[dict] = []
        self.rng = random.Random(seed)
        n = config.n_players
        if isinstance(strategies, Strategy):
            strategies = [strategies] * n
        if len(strategies) != n:
            raise ValueError(f"need {n} strategies, got {len(strategies)}")
        self.agents = [PlayerAgent(i, s, config.skills, config.selfish_pass_weight, self.rng)
                       for i, s in enumerate(strategies)]
        self.forced_left = dict(config.forced_misses)
        self.last_shot_possession = [0] * n
        self.log = GameLog(strategies=[s.name for s in strategies],
                           own_points=[0] * n, assisted_points=[0] * n)

    def play(self) -> GameLog:
        for poss in range(self.cfg.possessions_per_game):
            self._actions = []
            points = self._play_possession(poss)
            self.log.possession_points.append(points)
            if self.trace:
                self.log.timeline.append(self._snapshot(poss, points))
        self._score_utilities()
        return self.log

    def _record(self, **action) -> None:
        if self.trace:
            self._actions.append(action)

    def _snapshot(self, poss: int, points: int) -> dict:
        n = self.cfg.n_players
        return {
            "possession": poss,
            "points": points,
            "actions": self._actions,
            # skill_estimates[i][j]: what agent i believes about player j's skill
            "skill_estimates": [[a.estimated_skill(j) for j in range(n)] for a in self.agents],
            # trust[i][j]: agent i's reciprocity score for teammate j (None on the diagonal)
            "trust": [[None if j == a.idx else a.reciprocity(j) for j in range(n)] for a in self.agents],
        }

    def _score_utilities(self) -> None:
        lam, a = self.cfg.team_weight, self.cfg.assist_credit
        team = sum(self.log.possession_points)
        self.log.utilities = [
            lam * team + (1 - lam) * (own + a * assisted)
            for own, assisted in zip(self.log.own_points, self.log.assisted_points)
        ]

    # --- one possession -------------------------------------------------

    def _sample_look(self) -> Look:
        name, prob, points = self.rng.choices(ZONES, weights=ZONE_WEIGHTS)[0]
        return name, prob, points

    def _truly_better_to_pass(self, holder: int, looks) -> bool:
        """Would passing beat shooting for the team, judged with true skills?"""
        tov, skills = self.cfg.turnover_prob, self.cfg.skills
        value = lambda j: skills[j] * looks[j][1] * looks[j][2]
        best_pass = max((1 - tov) * value(j) for j in looks if j != holder)
        return best_pass - value(holder) > self.agents[holder].strategy.pass_margin

    def _play_possession(self, poss: int) -> int:
        cfg, n = self.cfg, self.cfg.n_players
        clock = cfg.shot_clock - self.rng.uniform(*cfg.setup_time)
        holder = cfg.start_holder if cfg.start_holder is not None else self.rng.randrange(n)
        looks = {j: self._sample_look() for j in range(n)}
        last_passer: Optional[int] = None
        self._record(type="start", player=holder)

        while True:
            better = None  # was passing truly better? (None when the shot was forced)
            if clock <= cfg.must_shoot_below:
                action, target = "shoot", holder   # forced: not a choice, so not judged
            else:
                since_shot = [poss - last for last in self.last_shot_possession]
                action, target = self.agents[holder].decide(looks, cfg.turnover_prob, since_shot)
                passed = action == "pass"
                better = self._truly_better_to_pass(holder, looks)
                self.log.decisions.append((poss, holder, better, passed))
                for agent in self.agents:
                    agent.observe_decision(holder, looks, passed, cfg.turnover_prob)

            if action == "shoot":
                made, points = self._shoot(poss, holder, looks[holder])
                self._record(type="shot", player=holder, zone=looks[holder][0], made=made, points=points,
                             forced=better is None, better_to_pass=bool(better))
                if made:
                    if last_passer is not None:
                        self.log.assisted_points[last_passer] += points
                    return points
                last_passer = None
                if self.rng.random() < cfg.offensive_rebound_prob:
                    holder = self.rng.randrange(n)  # [Oldham] random offensive rebounder
                    clock = cfg.offensive_rebound_clock
                    looks = {j: self._sample_look() for j in range(n)}
                    self._record(type="rebound", offense=True, player=holder)
                    continue
                self._record(type="rebound", offense=False, player=None)
                return 0

            stolen = self.rng.random() < cfg.turnover_prob
            self.log.passes.append((poss, holder, target, stolen))
            self.log.events.append((poss, f"P{holder} -> P{target}" + ("  STOLEN" if stolen else "")))
            self._record(type="pass", player=holder, to=target, stolen=stolen, better_to_pass=bool(better))
            if stolen:
                return 0
            clock -= self.rng.uniform(*cfg.pass_time)
            # The receiver keeps the look they were passed for; everyone else's changes.
            looks = {j: looks[j] if j == target else self._sample_look() for j in range(n)}
            last_passer = holder
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
        scored = points if made else 0
        self.log.own_points[shooter] += scored
        self.log.shots.append((poss, shooter, made, scored))
        self.log.events.append((poss, f"P{shooter} shoots ({look[0]}): " + (f"MADE {points}" if made else "miss")))
        return made, scored
