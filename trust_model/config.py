"""Parameters for the possession model and the agent strategies.

Values marked [Oldham] are taken from Oldham's NetLogo model
(code/hothand_version8.nlogo3d). Everything else is our own assumption and
should be stated as such in the report.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

# Shot zones: (name, base make probability, points). [Oldham, `score%` procedure]
ZONES = (
    ("restricted", 0.70, 2),
    ("key", 0.50, 2),
    ("mid_range", 0.43, 2),
    ("three", 0.33, 3),
)

# How often a player's current open look comes from each zone (assumption).
ZONE_WEIGHTS = (0.15, 0.20, 0.25, 0.40)

# Average base make probability, used to express the prior in "attempts".
MEAN_BASE_PROB = sum(w * z[1] for w, z in zip(ZONE_WEIGHTS, ZONES))

# Named skill profiles. A skill of 1.10 means 10% more likely to make any given look.
SKILL_PROFILES = {
    "equal": (1.0, 1.0, 1.0, 1.0, 1.0),
    "one_star": (1.0, 1.0, 1.25, 1.0, 0.9),
    "spread": (1.2, 1.1, 1.0, 0.9, 0.8),
}


@dataclass
class GameConfig:
    """The environment: rules of a possession. Fixed within an experiment."""

    skills: Tuple[float, ...] = SKILL_PROFILES["equal"]  # true ability, hidden from agents
    defensive_pressure: float = 0.0     # 0..1, cuts every make probability by this fraction
    possessions_per_game: int = 100     # roughly an NBA team's possessions per game

    # Payoffs (see GAME_THEORY.md). Each player's utility is
    #   u_i = team_weight * team points + (1 - team_weight) * (own points + assist_credit * assisted points)
    # team_weight = 1 is a pure team game; below s/b the possession is a Prisoner's Dilemma.
    team_weight: float = 1.0            # lambda
    assist_credit: float = 0.0          # a: personal credit for the points a pass sets up

    shot_clock: float = 24.0            # [Oldham]
    offensive_rebound_clock: float = 14.0
    setup_time: Tuple[float, float] = (4.0, 8.0)  # seconds to bring the ball up
    pass_time: Tuple[float, float] = (2.0, 4.0)   # seconds used by each pass
    must_shoot_below: float = 3.0       # holder shoots if the clock is this low

    pass_turnover_prob: float = 0.05    # [Oldham] 5% of passes lost
    pressure_turnover_bonus: float = 0.10  # extra turnover chance at full pressure
    offensive_rebound_prob: float = 0.24   # [Oldham]
    max_make_prob: float = 0.95

    # Who brings the ball up; None = random. Oldham always inbounds to spot 0, but a
    # fixed ball handler takes ~half the shots and is never "passed to", which
    # confounds the exclusion measures, so we make it random.
    start_holder: Optional[int] = None

    # Induced slump: {player index: number of first shots forced to miss}.
    # Lets us create "a capable shooter misses several attempts" on purpose.
    forced_misses: Dict[int, int] = field(default_factory=dict)

    # Event that starts the recovery clock in the metrics.
    cold_run_length: int = 3
    # A cold player counts as "excluded" if no pass reaches them within this
    # many possessions. Runs starting closer than this to the end of the game
    # are skipped, so the end of the game isn't mistaken for exclusion.
    recovery_window: int = 20

    @property
    def n_players(self) -> int:
        return len(self.skills)

    @property
    def turnover_prob(self) -> float:
        return self.pass_turnover_prob + self.pressure_turnover_bonus * self.defensive_pressure

    @property
    def selfish_pass_weight(self) -> float:
        """How much a pass is worth to a purely self-interested passer, per point it sets up."""
        return self.team_weight + (1 - self.team_weight) * self.assist_credit


@dataclass(frozen=True)
class Strategy:
    """How an agent remembers and decides. Agents on one team may use different strategies.

    cooperation:
      "always"     - acts in the team's interest whatever its payoff (unconditional cooperator)
      "never"      - myopic best response to its own payoff (hog / always defect)
      "reciprocal" - cooperates as much as teammates have recently cooperated (memory-k tit-for-tat)
    """

    name: str
    memory_length: Optional[int] = None  # last k shots (and k decisions) remembered per player; None = whole game
    cooperation: str = "always"
    exploration: float = 0.0             # forgiveness: chance of passing to the most overlooked teammate
    pass_margin: float = 0.2             # pass only if a teammate's look is worth this many more expected points
    prior_strength: float = 3.0          # belief starts as if each player had this many average attempts
    oracle: bool = False                 # baseline: agents know everyone's true skill
    know_own_skill: bool = True          # agents judge themselves by true skill (isolates trust in teammates)


STRATEGIES = {
    # Unconditional cooperators: the original learning-model strategies.
    "short_memory": Strategy("short_memory", memory_length=5),
    "long_memory": Strategy("long_memory", memory_length=30),
    "short_memory_explore": Strategy("short_memory_explore", memory_length=5, exploration=0.10),
    "oracle": Strategy("oracle", oracle=True),
    # Strategies for the game: defect, reciprocate, reciprocate with forgiveness.
    "hog": Strategy("hog", memory_length=5, cooperation="never"),
    "reciprocator": Strategy("reciprocator", memory_length=5, cooperation="reciprocal"),
    "forgiving_reciprocator": Strategy("forgiving_reciprocator", memory_length=5,
                                       cooperation="reciprocal", exploration=0.10),
    "long_reciprocator": Strategy("long_reciprocator", memory_length=30, cooperation="reciprocal"),
}

# The strategy set for the meta-game (metagame.py). short_memory is the unconditional cooperator.
META_STRATEGIES = ("short_memory", "hog", "reciprocator", "forgiving_reciprocator", "long_reciprocator")
