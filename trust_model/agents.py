"""Player agents: memory, beliefs, and the shoot-or-pass decision."""
import random
from collections import deque
from typing import Dict, List, Sequence, Tuple

from .config import MEAN_BASE_PROB, Strategy

Look = Tuple[str, float, int]  # (zone name, make probability for an average player, points)


class PlayerAgent:
    """One of the five players.

    Skill memory: for every player on the team (including itself), the last k
    shot attempts it has seen, stored as (made, expected make probability).

    Skill belief: an estimate of each player's skill relative to an average shooter,
        (makes + prior) / (expected makes + prior)
    where `prior` is `prior_strength` average attempts. 1.0 means "average".
    Dividing by expected makes means a missed three counts against a player
    less than a missed layup.

    Cooperation memory: for every teammate, its last k decisions at moments
    when (in this agent's view) passing was better for the team. True = passed
    (cooperated), False = shot anyway (defected). Used by reciprocal strategies.
    """

    def __init__(self, idx: int, strategy: Strategy, true_skills: Sequence[float],
                 selfish_pass_weight: float, rng: random.Random):
        self.idx = idx
        self.strategy = strategy
        self.true_skills = true_skills
        self.selfish_pass_weight = selfish_pass_weight
        self.rng = rng
        n = len(true_skills)
        self.memory: Dict[int, deque] = {j: deque(maxlen=strategy.memory_length) for j in range(n)}
        self.coop_memory: Dict[int, deque] = {j: deque(maxlen=strategy.memory_length) for j in range(n)}
        self._prior = strategy.prior_strength * MEAN_BASE_PROB

    # --- memory ---------------------------------------------------------

    def observe_shot(self, shooter: int, made: bool, expected_prob: float) -> None:
        self.memory[shooter].append((made, expected_prob))

    def observe_decision(self, holder: int, looks: Dict[int, Look], passed: bool,
                         turnover_prob: float) -> None:
        """Judge a teammate's choice. Only moments when a pass was clearly better
        for the team (by this agent's own beliefs) count as a test of cooperation."""
        if holder == self.idx:
            return
        if self.team_gain_from_passing(holder, looks, turnover_prob) > self.strategy.pass_margin:
            self.coop_memory[holder].append(passed)

    # --- beliefs --------------------------------------------------------

    def estimated_skill(self, j: int) -> float:
        if self.strategy.oracle or (j == self.idx and self.strategy.know_own_skill):
            return self.true_skills[j]
        mem = self.memory[j]
        makes = sum(1 for made, _ in mem if made)
        expected = sum(p for _, p in mem)
        return (makes + self._prior) / (expected + self._prior)

    def expected_points(self, j: int, look: Look) -> float:
        _, prob, points = look
        return self.estimated_skill(j) * prob * points

    def team_gain_from_passing(self, holder: int, looks: Dict[int, Look], turnover_prob: float) -> float:
        """Expected team points gained if `holder` passed to the best teammate instead of shooting."""
        best_pass = max((1 - turnover_prob) * self.expected_points(j, looks[j]) for j in looks if j != holder)
        return best_pass - self.expected_points(holder, looks[holder])

    def reciprocity(self, j: int) -> float:
        """How cooperative teammate j has been lately: 1 = always passed when it should.
        Starts at 1 (cooperate first, as in tit-for-tat)."""
        mem = self.coop_memory[j]
        return (sum(mem) + 1) / (len(mem) + 1)

    def cooperation_level(self, j: int) -> float:
        """0..1: how far this agent puts the team's interest ahead of its own
        when deciding whether to give the ball to teammate j."""
        mode = self.strategy.cooperation
        if mode == "always":
            return 1.0
        if mode == "never":
            return 0.0
        return self.reciprocity(j)

    def pass_weight(self, j: int) -> float:
        """Value to this agent of each point a pass to j sets up: between the
        selfish value (team_weight + assist credit) and 1 (team-first)."""
        base = self.selfish_pass_weight
        return base + (1 - base) * self.cooperation_level(j)

    # --- decision -------------------------------------------------------

    def decide(self, looks: Dict[int, Look], turnover_prob: float,
               possessions_since_shot: List[int]) -> Tuple[str, int]:
        """Return ("shoot", self) or ("pass", teammate).

        Shooting is worth the agent's own expected points: they count both for
        the team and for the agent. A pass to j is worth j's expected points
        times `pass_weight(j)`, which depends on the strategy (and, for
        reciprocators, on how cooperative j has been). Pass only if that beats
        shooting by `pass_margin`.

        Forgiveness: with probability `exploration`, pass to the teammate who
        has gone longest without a shot attempt instead.
        """
        teammates = [j for j in looks if j != self.idx]

        if self.strategy.exploration and self.rng.random() < self.strategy.exploration:
            longest = max(possessions_since_shot[j] for j in teammates)
            overlooked = [j for j in teammates if possessions_since_shot[j] == longest]
            return "pass", self.rng.choice(overlooked)

        shoot_value = self.expected_points(self.idx, looks[self.idx])
        pass_values = {j: self.pass_weight(j) * (1 - turnover_prob) * self.expected_points(j, looks[j])
                       for j in teammates}
        best = max(pass_values.values())
        target = self.rng.choice([j for j, v in pass_values.items() if v == best])

        if shoot_value + self.strategy.pass_margin >= best:
            return "shoot", self.idx
        return "pass", target
