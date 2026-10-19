"""Player agents: memory, beliefs, and the shoot-or-pass decision."""
import random
from collections import deque
from typing import Dict, List, Sequence, Tuple

from .config import MEAN_BASE_PROB, Strategy

Look = Tuple[str, float, int]  # (zone name, make probability for an average player, points)


class PlayerAgent:
    """One of the five players.

    Memory: for every player on the team (including itself), the last k shot
    attempts it has seen, stored as (made, expected make probability).

    Belief: an estimate of each player's skill relative to an average shooter,
        (makes + prior) / (expected makes + prior)
    where `prior` is `prior_strength` average attempts. 1.0 means "average".
    Dividing by expected makes means a missed three counts against a player
    less than a missed layup.
    """

    def __init__(self, idx: int, strategy: Strategy, true_skills: Sequence[float],
                 rng: random.Random):
        self.idx = idx
        self.strategy = strategy
        self.true_skills = true_skills
        self.rng = rng
        n = len(true_skills)
        self.memory: Dict[int, deque] = {j: deque(maxlen=strategy.memory_length) for j in range(n)}
        self._prior = strategy.prior_strength * MEAN_BASE_PROB

    # --- memory ---------------------------------------------------------

    def observe_shot(self, shooter: int, made: bool, expected_prob: float) -> None:
        self.memory[shooter].append((made, expected_prob))

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

    # --- decision -------------------------------------------------------

    def decide(self, looks: Dict[int, Look], turnover_prob: float,
               possessions_since_shot: List[int]) -> Tuple[str, int]:
        """Return ("shoot", self) or ("pass", teammate).

        Greedy rule: compare the value of my shot now with the best teammate's
        look, discounted by the chance the pass is stolen. Pass only if the
        teammate's look is better by at least `pass_margin` expected points.
        Exploration: with probability `exploration`, pass to the teammate who
        has gone longest without a shot attempt instead.
        """
        teammates = [j for j in looks if j != self.idx]

        if self.strategy.exploration and self.rng.random() < self.strategy.exploration:
            longest = max(possessions_since_shot[j] for j in teammates)
            overlooked = [j for j in teammates if possessions_since_shot[j] == longest]
            return "pass", self.rng.choice(overlooked)

        shoot_value = self.expected_points(self.idx, looks[self.idx])
        pass_values = {j: (1 - turnover_prob) * self.expected_points(j, looks[j]) for j in teammates}
        best = max(pass_values.values())
        target = self.rng.choice([j for j, v in pass_values.items() if v == best])

        if shoot_value + self.strategy.pass_margin >= best:
            return "shoot", self.idx
        return "pass", target
