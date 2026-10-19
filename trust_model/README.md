# When Teammates Stop Passing: trust_model

A possession-level multiagent model of how memory of teammates' misses shapes
passing. Simplified from Oldham's *Drafting agent-based modeling into
basketball analytics* (CoMSES, 2019), the NetLogo model in `../code/`.

**Question:** How does the length of teammates' memory affect passing decisions
and team scoring, and can occasionally passing to overlooked players prevent
lasting exclusion after a run of misses?

## Running it

Needs Python 3.8+ and nothing else.

```bash
# from the 4457BasketballSimulator folder
python3 -m trust_model.demo                         # play-by-play of one game
python3 -m trust_model.demo --strategy long_memory
python3 -m trust_model.experiments --games 300      # full grid (~30 s)
```

Experiments write `trust_model/results/raw.csv` (one row per game) and
`summary.csv` (mean and 95% CI per cell).

## Files

| File | What it is |
|---|---|
| `config.py` | All parameters: shot zones, game rules, skill profiles, strategies |
| `agents.py` | `PlayerAgent`: memory, skill estimates, shoot-or-pass decision |
| `environment.py` | `Game`: runs possessions, resolves shots, passes, rebounds |
| `metrics.py` | Points per possession, pass inequality, exclusion and recovery |
| `experiments.py` | Runs the experiment grid in parallel |
| `demo.py` | Prints one game play by play |

## The model

**Agents.** Five players. Each has a true skill (a multiplier on make
probability, fixed for the experiment) that no agent can see.

**Memory.** Every agent remembers the last *k* shot attempts it has seen from
each player, as (made?, chance an average player makes that shot).

**Belief.** Estimated skill of player *j* = (makes + prior) / (expected makes +
prior), where the prior is worth 3 average attempts. 1.0 means average. Because
it divides by expected makes, a missed three hurts less than a missed layup.

**Decision.** At every step, each player has a current open look (a shot zone).
The ball holder compares:
- shooting now: own skill × look's make probability × points, against
- passing to teammate *j*: (1 − turnover chance) × *j*'s estimated skill × *j*'s look × points.

The holder passes to the best teammate only if that teammate's look is worth
at least 0.2 more expected points. With *exploration* turned on, with
probability ε the holder instead passes to the teammate who has gone longest
without a shot attempt. When the shot clock is under 3 s, the holder must shoot.

**Possession.** A random player brings the ball up (4–8 s). Each pass uses
2–4 s. A miss is rebounded by the offense 24% of the time (random player, 14 s
clock). Otherwise the possession ends on a make, a defensive rebound or a steal.

**Defensive pressure** (0–1) cuts every make probability by that fraction and
raises the turnover chance by up to 10 percentage points.

**Induced slump.** `forced_misses={2: 3}` makes player 2's first three shots
miss, creating "a capable shooter who misses several attempts" on demand.

### Strategies compared

| Strategy | Memory *k* | Exploration ε |
|---|---|---|
| `short_memory` | last 5 attempts | 0 |
| `long_memory` | last 30 attempts | 0 |
| `short_memory_explore` | last 5 attempts | 0.10 |
| `oracle` (baseline) | knows true skills | 0 |

### Measures

- **points_per_possession**: team performance
- **gini_passes_received**: how unevenly passes are spread (0 = even)
- **excluded_rate**: share of cold runs (3 straight misses) after which the
  player gets no pass for 20 possessions
- **mean_recovery_possessions**: possessions until a cold player's next pass,
  when one comes within 20
- **slump_player_pass_share**: the induced-slump player's share of all passes
- **best_shooter_shot_share**: share of shots taken by the most skilled player

### Formal framing

From each passer's point of view this is a **multi-armed bandit**. Teammates are
arms with unknown success rates. Memory length is a sliding-window estimator.
Passing to overlooked players is ε-greedy exploration. Lasting exclusion is the
**hot stove effect** (Denrell & March, 2001, *Organization Science* 12(5)): a
greedy learner stops sampling an option after bad early outcomes, so its low
estimate never gets corrected.

## What we kept from Oldham, and what we changed

| | Oldham | Ours |
|---|---|---|
| Zone make probabilities | 70 / 50 / 43 / 33% | same |
| Shot clock | 24 s | same |
| Pass turnover | 5% | same, plus pressure |
| Offensive rebound | 24%, random player | same |
| Player skill | identical for all | individual, fixed |
| Pass target | max of FG% + team share + hot streak + star bias, among nearby teammates | expected points from each agent's own memory |
| Memory | whole-game FG%, and current hot streak | last *k* attempts |
| Shoot or pass | shot quality, clock, hot streak, star bias | own shot vs best teammate's |
| Space | 3D court, movement, vision cone | none: each player has an open look each step |
| Ball handler | always spot 0 | random, so no player is structurally excluded |
| Opponent | full team | defensive pressure only |

Assumptions to state in the report: zone frequencies (15/20/25/40%), the
prior of 3 attempts, the 0.2-point pass margin, pass and setup times, the
pressure effect on turnovers, and the 20-possession exclusion window.

## Notes for next steps

- Points per possession is about 1.3 with no pressure, above the NBA's ~1.1.
  Pressure 0.15 lands near real values, so consider using it as the default.
- Passes per possession (~0.5) is lower than real basketball because only
  decision-relevant passes are modelled, not ball movement.
- Sweep *k* (e.g. 3, 5, 10, 20, 30, whole game) and ε (0, 0.05, 0.1, 0.2) as
  continuous axes instead of three fixed strategies.
- Possible extensions: memory that decays by time instead of attempts,
  agents that don't all see every shot (`observe_shot` per agent), UCB or
  Thompson sampling instead of ε-greedy.
