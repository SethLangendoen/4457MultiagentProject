# When Teammates Stop Passing: trust_model

A possession-level multiagent model of how memory of teammates' misses shapes
passing. Simplified from Oldham's *Drafting agent-based modeling into
basketball analytics* (CoMSES, 2019), the NetLogo model in `../code/`.

**Question:** How does the length of teammates' memory affect passing decisions
and team scoring, can occasionally passing to overlooked players prevent
lasting exclusion after a run of misses, and which of these strategies are
stable when players are partly self-interested?

**The game theory behind the model is explained in [GAME_THEORY.md](GAME_THEORY.md).**

## Running it

Needs Python 3.8+ and nothing else.

```bash
# from the 4457BasketballSimulator folder
python3 -m trust_model.stage_game                   # two-player game solved exactly
python3 -m trust_model.demo                         # play-by-play of one game
python3 -m trust_model.demo --team-weight 0.6 --strategy hog,reciprocator,reciprocator,short_memory,forgiving_reciprocator
python3 -m trust_model.experiments --games 200      # whole-team strategies (~2.5 min)
python3 -m trust_model.metagame                     # mixed teams: equilibria (~1 min)
python3 -m trust_model.viz                          # visualiser at http://localhost:8000
```

### Visualiser

`python3 -m trust_model.viz` starts a local web page (standard library only;
`--port` to change the port, `--no-browser` to not open a browser). The page
asks the Python model to run; it doesn't simulate anything itself.

- **Single game:** choose a strategy per seat, λ, skills, pressure and slump, then
  play through the game possession by possession. It shows the passes and shots,
  a running score and cooperation rate, who receives passes, teammates' belief
  about each player's skill against their true skill, and a who-trusts-whom matrix.
- **Meta-game:** runs the 126-mix payoff table for a chosen λ and shows replicator
  dynamics from six starting mixes plus the Nash check. Use 100+ games per mix
  before drawing conclusions.

URL options: `?p=60` jumps to possession 60, `?tab=meta` opens and runs the
meta-game, `?theme=light` or `?theme=dark` forces a theme.

Experiments write `trust_model/results/raw.csv` (one row per game) and
`summary.csv` (mean and 95% CI per cell). The meta-game writes
`metagame_lambda_<λ>.csv` (payoff table) and prints the equilibrium analysis.

## Files

| File | What it is |
|---|---|
| `config.py` | All parameters: shot zones, game rules, payoffs (λ, assist credit), skill profiles, strategies |
| `agents.py` | `PlayerAgent`: memory, skill estimates, reciprocity, shoot-or-pass decision |
| `environment.py` | `Game`: runs possessions, resolves shots, passes, rebounds; scores each player's payoff |
| `metrics.py` | Points per possession, cooperation rate, pass inequality, exclusion and recovery |
| `experiments.py` | Runs the experiment grid (every player uses one strategy) in parallel |
| `metagame.py` | Empirical game-theoretic analysis: mixed teams, Nash check, replicator dynamics |
| `stage_game.py` | The two-player Pass-or-Hog game: payoff matrix, Nash equilibria, thresholds |
| `demo.py` | Prints one game play by play |
| `viz.py`, `static/index.html` | Local visualiser: server and page |
| `GAME_THEORY.md` | The game-theoretic foundation, derivations and results |
| `DIFFERENCES_FROM_REFERENCE.md` | Full comparison with Oldham's model |

## The model

**Agents.** Five players. Each has a true skill (a multiplier on make
probability, fixed for the experiment) that no agent can see.

**Memory.** Every agent remembers the last *k* shot attempts it has seen from
each player, as (made?, chance an average player makes that shot).

**Belief.** Estimated skill of player *j* = (makes + prior) / (expected makes +
prior), where the prior is worth 3 average attempts. 1.0 means average. Because
it divides by expected makes, a missed three hurts less than a missed layup.

**Payoffs.** Each player's payoff is
λ · team points + (1 − λ) · (own points + a · assisted points).
λ = 1 (the default) is a pure team game. Below λ ≈ s/b, passing becomes a
Prisoner's Dilemma (see [GAME_THEORY.md](GAME_THEORY.md)).

**Decision.** At every step, each player has a current open look (a shot zone).
The ball holder compares:
- shooting now: own skill × look's make probability × points, against
- passing to teammate *j*: w × (1 − turnover chance) × *j*'s estimated skill × *j*'s look × points.

The weight w depends on the strategy. It is 1 for a team-first player,
λ + (1 − λ)a for a selfish one, and in between for a reciprocator, according to
how often *j* has passed when it should have. The holder passes to the best
teammate only if that is worth at least 0.2 more expected points. With
*forgiveness* (exploration) turned on, with probability ε the holder instead
passes to the teammate who has gone longest without a shot attempt. When the
shot clock is under 3 s, the holder must shoot.

**Reciprocity.** Every agent judges each teammate's decisions. When passing
would clearly have helped the team (by the observer's beliefs), passing counts
as cooperating and shooting as defecting. Reciprocators remember the last *k*
such tests per teammate.

**Possession.** A random player brings the ball up (4–8 s). Each pass uses
2–4 s. A miss is rebounded by the offense 24% of the time (random player, 14 s
clock). Otherwise the possession ends on a make, a defensive rebound or a steal.

**Defensive pressure** (0–1) cuts every make probability by that fraction and
raises the turnover chance by up to 10 percentage points.

**Induced slump.** `forced_misses={2: 3}` makes player 2's first three shots
miss, creating "a capable shooter who misses several attempts" on demand.

### Strategies compared

| Strategy | Memory *k* | Cooperation | Forgiveness ε |
|---|---|---|---|
| `short_memory` | last 5 | always | 0 |
| `long_memory` | last 30 | always | 0 |
| `short_memory_explore` | last 5 | always | 0.10 |
| `oracle` (baseline) | knows true skills | always | 0 |
| `hog` | last 5 | never | 0 |
| `reciprocator` | last 5 | reciprocal | 0 |
| `forgiving_reciprocator` | last 5 | reciprocal | 0.10 |
| `long_reciprocator` | last 30 | reciprocal | 0 |

Teams can mix strategies: `Game(config, [s0, s1, s2, s3, s4], seed)`.

### Measures

- **points_per_possession**: team performance
- **efficiency_vs_oracle**: points per possession ÷ the oracle team's in the same conditions
- **cooperation_rate**: of the moments when passing truly was better (by true skills), the share where the holder passed
- **mean_utility**: average player payoff
- **gini_passes_received**: how unevenly passes are spread (0 = even)
- **excluded_rate**: share of cold runs (3 straight misses) after which the
  player gets no pass for 20 possessions
- **mean_recovery_possessions**: possessions until a cold player's next pass,
  when one comes within 20
- **slump_player_pass_share**: the induced-slump player's share of all passes
- **best_shooter_shot_share**: share of shots taken by the most skilled player

### Formal framing

The model is a **repeated game with incomplete information**, analysed in
three layers (full detail in [GAME_THEORY.md](GAME_THEORY.md)):

1. **Stage game:** a two-player Pass-or-Hog game, which is a Prisoner's Dilemma when λ < s/b.
2. **Repeated game:** five players with hidden skill types, beliefs learned from
   noisy shot outcomes, and memory-*k* strategies (cooperate, defect, tit-for-tat,
   generous tit-for-tat).
3. **Meta-game:** empirical game-theoretic analysis of mixed teams to find which
   strategies are Nash equilibria and which survive replicator dynamics.

Within it, each agent's skill-belief problem is a **multi-armed bandit**.
Lasting exclusion is the **hot stove effect** (Denrell & March, 2001,
*Organization Science* 12(5)): a greedy learner stops sampling an option after
bad early outcomes, so its low estimate never gets corrected.

## What we kept from Oldham, and what we changed

Summary below; the full comparison, with links to Oldham's code, is in
[DIFFERENCES_FROM_REFERENCE.md](DIFFERENCES_FROM_REFERENCE.md).

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
  continuous axes instead of a few fixed strategies.
- Sweep assist credit in the meta-game to test whether it makes forgiveness stable (H5 in GAME_THEORY.md).
- Run the meta-game with more games per profile (`--games 500`) for final results.
- Possible extensions: memory that decays by time instead of attempts,
  agents that don't all see every shot (`observe_shot` per agent), UCB or
  Thompson sampling instead of ε-greedy.
