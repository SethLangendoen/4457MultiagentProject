# How trust_model differs from the reference model

This document compares our model (`trust_model/`) with the model it is based on:

> Oldham, M. (2019). *Drafting agent-based modeling into basketball analytics*
> (Version 1.0.0). CoMSES Net. File: [`code/hothand_version8.nlogo3d`](../code/hothand_version8.nlogo3d)

Line links such as [L455](../code/hothand_version8.nlogo3d#L455) point to the
relevant code in Oldham's NetLogo file.

---

## 1. Summary

The two models ask different questions.

| | Oldham's model | Our model |
|---|---|---|
| **Question** | Do the hot-hand belief and favouring a franchise player change game outcomes? | Does the length of teammates' memory cause capable players to be frozen out after a run of misses, and does occasional exploration prevent it? |
| **Focus** | A full game of basketball | The shoot-or-pass decision within possessions |
| **Formal model** | Agent-based simulation with fixed decision rules | Repeated game with incomplete information: a Pass-or-Hog Prisoner's Dilemma, memory-based strategies, and empirical game-theoretic analysis (see [GAME_THEORY.md](GAME_THEORY.md)) |
| **Platform** | NetLogo 3D 6.0.4 | Python 3 (standard library only) |
| **Scale** | One game per run, slow to batch | ~21,600 games in ~30 s |

Our model keeps Oldham's basketball numbers and his central idea: **what
teammates believe about a player determines who gets the ball**. It drops the
spatial simulation and adds the parts our question needs: individual skill,
controllable memory, explicit beliefs, exploration and exclusion measures.

---

## 2. What we kept

These values come directly from Oldham's model.

| Element | Value | Where in Oldham |
|---|---|---|
| Make probability, restricted area | 70% | [L152](../code/hothand_version8.nlogo3d#L152) |
| Make probability, key | 50% | [L156](../code/hothand_version8.nlogo3d#L156) |
| Make probability, mid-range | 43% | [L153](../code/hothand_version8.nlogo3d#L153) |
| Make probability, three-point | 33% | [L151](../code/hothand_version8.nlogo3d#L151) |
| Shot clock | 24 seconds | [L160](../code/hothand_version8.nlogo3d#L160) |
| Pass turnover chance | 5% | [L468](../code/hothand_version8.nlogo3d#L468) |
| Offensive rebound chance | 24% | [L685](../code/hothand_version8.nlogo3d#L685) |
| Offensive rebounder | random player on the attacking team | [L688](../code/hothand_version8.nlogo3d#L688) |
| Team size | 5 players | [L186](../code/hothand_version8.nlogo3d#L186) |
| Core mechanism | Passing depends on a teammate's past performance | [L286-297](../code/hothand_version8.nlogo3d#L286-L297), [L455](../code/hothand_version8.nlogo3d#L455) |

We dropped Oldham's half-court (2%) and backcourt (0%) shots, because players
in our model only take shots from realistic zones.

---

## 3. What we changed

Each change below lists what Oldham does, what we do, and why.

### 3.1 Player skill: identical → individual

**Oldham:** a shot's success depends only on the zone it's taken from
([L555-559](../code/hothand_version8.nlogo3d#L555-L559)). Every player has the
same percentages.

**Ours:** each player has a fixed, hidden **true skill** that multiplies the
zone percentage. Make chance = zone % × skill × (1 − defensive pressure).
Skill profiles are in `config.py` → `SKILL_PROFILES`.

**Why:** our question is about *capable* players being overlooked after
*unlucky* misses. If everyone has the same skill, no player is more capable
than another, and a miss never tells you anything about the shooter. True
skill gives us a ground truth: we can tell whether a player is avoided because
they really are worse or only because of bad luck.

### 3.2 Memory: two fixed forms → a tunable window

**Oldham:** two kinds of memory, neither adjustable.
- `fg%` = made ÷ attempted over the whole game ([L603](../code/hothand_version8.nlogo3d#L603)), which never forgets.
- `hot_streak` = consecutive makes, reset to 0 on any miss ([L596](../code/hothand_version8.nlogo3d#L596)), which only remembers the current streak.

**Ours:** each agent remembers the last ***k*** attempts by each player,
storing whether the shot went in and how likely an average player was to make
it. *k* is a parameter (`Strategy.memory_length`): 5 for short memory, 30 for
long, or `None` for the whole game.

**Why:** memory length is our independent variable. Oldham's two forms are the
two extremes of a scale we need to explore.

### 3.3 Beliefs: a raw score → a skill estimate with a prior

**Oldham:** `attract_to_pass` = `fg%` + share of team points + hot-streak term
(+ star bias) ([L290-291](../code/hothand_version8.nlogo3d#L290-L291)).
It adds quantities on different scales and treats a missed three the same as a
missed layup.

**Ours:** estimated skill = (makes + prior) ÷ (expected makes + prior), in
`agents.py` → `estimated_skill()`.
- Dividing by expected makes adjusts for shot difficulty, so a missed three
  costs less than a missed layup.
- The prior (worth 3 average attempts) starts everyone at 1.0 (average) and
  stops a single shot from swinging the estimate.

**Why:** we need an estimate that is directly comparable to true skill, so we
can measure how wrong beliefs are and when they mislead.

### 3.4 Whose belief: one shared value → beliefs held by each agent

**Oldham:** `attract_to_pass` belongs to the *receiving* player
([L286-297](../code/hothand_version8.nlogo3d#L286-L297)), so every teammate
reads the same number. It works as a public reputation.

**Ours:** each `PlayerAgent` keeps its own memory of every player and forms its
own estimates.

**Why:** in a multiagent system, beliefs belong to agents. This makes it
possible to give agents different memory lengths or different observations.

**Current limitation:** at present every agent sees every shot and all agents
use the same *k*, so their beliefs about any teammate are identical. In practice
it still behaves like a shared reputation until we add partial observation or
mixed memory lengths (see Section 7).

### 3.5 Shoot-or-pass: own situation only → compare self with teammates

**Oldham:** the ball holder's choice ([L423-442](../code/hothand_version8.nlogo3d#L423-L442))
compares a score built from shot-clock time, own shot quality, hot streak and
star bias against a random threshold. It never considers how good a teammate's
shot would be.

**Ours:** the holder compares expected points (`agents.py` → `decide()`):
- **shoot:** own skill × own look's make chance × points
- **pass to *j*:** (1 − turnover chance) × *j*'s *estimated* skill × *j*'s look's make chance × points

The holder passes to the best teammate only if that teammate is worth at least
0.2 more expected points (the pass margin). When the shot clock is under
3 seconds, the holder must shoot.

**Why:** our proposal defines the decision as "whether to shoot or pass based
on shot quality and its estimate of teammates' shooting ability." Comparing
self with teammates is what makes a mistaken belief costly.

### 3.6 Choosing whom to pass to: always the top teammate → optional exploration

**Oldham:** `max-one-of players_in_prox [attract_to_pass]`
([L455](../code/hothand_version8.nlogo3d#L455)) always chooses the top-rated
nearby teammate.

**Ours:** the same greedy choice by default. With exploration ε > 0, on a
fraction ε of decisions the holder passes to **the teammate who has gone
longest without a shot attempt** (`Strategy.exploration`).

**Why:** this is our third strategy, "occasionally giving overlooked players
another opportunity." Without exploration, an excluded player never shoots, so
teammates never get new information about them. Exploration is the standard
fix for this in learning models (ε-greedy).

### 3.7 Who can receive a pass: geometry → everyone

**Oldham:** only teammates inside a vision cone of radius 6 and 310°, who are
within 3 patches of their own target spot, can receive a pass
([L450](../code/hothand_version8.nlogo3d#L450)). Often nobody qualifies.

**Ours:** every teammate is always a possible receiver. Each has a randomly
drawn current **look** (shot zone), and the receiver keeps the look they were
passed for.

**Why:** with geometry, a player might stop getting the ball because of where
they are standing, not because teammates distrust them. Removing geometry
isolates the effect of belief.

### 3.8 Space and time: 3D court and ticks → abstract possessions

**Oldham:** a 3D court (51 × 97 × 13 patches); players move each tick, and
defenders follow their assigned opponent
([L369-382](../code/hothand_version8.nlogo3d#L369-L382),
[L744-752](../code/hothand_version8.nlogo3d#L744-L752)). One tick = 0.5 s
([L269](../code/hothand_version8.nlogo3d#L269)); a game is 5,760 ticks
([L774](../code/hothand_version8.nlogo3d#L774)).

**Ours:** no positions or movement. Time is the shot clock within a possession:
4–8 s to bring the ball up and 2–4 s per pass. A game is 100 possessions.

**Why:** movement adds noise and runtime without informing our question. Our
proposal commits to "possessions rather than reproducing every feature of a
full basketball game."

### 3.9 Who brings the ball up: always one player → random

**Oldham:** the inbound pass always goes to spot 0 or spot 5
([L633](../code/hothand_version8.nlogo3d#L633),
[L715](../code/hothand_version8.nlogo3d#L715)).

**Ours:** a random player starts each possession (`GameConfig.start_holder = None`).

**Why:** in our first test with a fixed ball handler, that player took about
half the team's shots and almost never received passes. They looked
"excluded" by design, which distorted the exclusion measures.

### 3.10 Opponent: a full team → defensive pressure

**Oldham:** two five-player teams alternate possessions; steals happen with a
small chance each tick ([L270-271](../code/hothand_version8.nlogo3d#L270-L271)).

**Ours:** only one team's offence is simulated. The opponent appears as
**defensive pressure** (0–1), which lowers every make chance by that fraction
and raises the turnover chance by up to 10 percentage points. Possessions end
on a make, a defensive rebound or a steal.

**Why:** our question is about cooperation inside one team. Pressure lets us
vary how hard scoring is, which our proposal lists as an experimental factor.

### 3.11 Payoffs: none → each player has a utility

**Oldham:** players have no payoffs. They follow fixed rules, and the model
records team scores.

**Ours:** each player's utility is
λ · team points + (1 − λ) · (own points + a · assisted points)
(`GameConfig.team_weight`, `GameConfig.assist_credit`; scored in
`Game._score_utilities()`). Players can follow different strategies:
cooperate, hog, reciprocate, or reciprocate with forgiveness.

**Why:** game theory needs players whose interests can conflict. With λ < 1,
passing becomes a Prisoner's Dilemma and cooperation has to be sustained by
strategy. That lets us ask which strategies are equilibria. The derivation
and results are in [GAME_THEORY.md](GAME_THEORY.md).

---

## 4. What we added

| Addition | Where | Purpose |
|---|---|---|
| Induced slump | `GameConfig.forced_misses` | Force a chosen player's first *n* shots to miss, creating "a capable shooter who misses several attempts" on demand |
| Oracle strategy | `STRATEGIES["oracle"]` | Comparison group whose agents know true skills, showing how much exclusion would happen anyway |
| Exclusion rate | `metrics.py` | Share of cold runs (3 straight misses) followed by no pass for 20 possessions |
| Recovery time | `metrics.py` | Possessions until a cold player receives a pass again |
| Pass and shot inequality | `metrics.py` → `gini()` | How evenly opportunities are shared |
| Slump player's pass share | `metrics.py` | How the induced-slump player is treated |
| Experiment grid | `experiments.py` | 4 strategies × 3 skill profiles × 3 pressures × slump on/off, run in parallel with shared random seeds |
| Play-by-play demo | `demo.py` | Shows decisions and final beliefs for one game |
| Individual payoffs (λ, assist credit) | `GameConfig`, `Game._score_utilities()` | Turn the possession into a game with partly conflicting interests |
| Reciprocity | `PlayerAgent.observe_decision()`, `reciprocity()` | Tit-for-tat-style strategies that respond to teammates' cooperation |
| Mixed teams | `Game(config, [five strategies], seed)` | Players with different strategies on one team |
| Cooperation rate, efficiency vs oracle | `metrics.py`, `experiments.py` | How often the better pass was made; points lost to wrong beliefs and selfishness |
| Stage-game solver | `stage_game.py` | Payoff matrix, Nash equilibria, Prisoner's Dilemma threshold, folk-theorem and assist-credit thresholds |
| Meta-game analysis | `metagame.py` | Payoff table over 126 team mixes, Nash check, replicator dynamics |

---

## 5. What we removed

| Removed | Why |
|---|---|
| Hot-hand bias (`hot_hand_factor`, `streak_size`) | Our question is about memory of misses, not belief in streaks. A streak is one particular kind of short memory, so it could be added back as a strategy. |
| Franchise-player bias (`bias_to_gun`, `home_gun`, `away_gun`) | Not part of our question. Could be added back as a fixed bonus in `decide()`. |
| Share of team points (`team%`) | Mixed shot volume with accuracy; our skill estimate replaces it. |
| Court drawing, movement, defenders, inbound positioning | See 3.7 and 3.8. |
| Half-court and backcourt shots | Only reachable through movement; not relevant. |
| Second team, lead changes, max lead | We measure our team's offence only. |
| NetLogo `gis` extension | Loaded by Oldham's model but never used. |

---

## 6. Problems in the reference model we avoided

We found these issues while reading Oldham's code. They don't affect our model,
because we didn't reuse that code, but anyone citing his results should know
about them.

1. **The hot-hand slider works backwards.** `hh = 1 / hot_hand_factor`
   ([L184](../code/hothand_version8.nlogo3d#L184)). A slider value of 0.1
   gives the *strongest* effect (×10), 1.0 the weakest (×1), and 0 turns it
   off, so the scale isn't continuous.
2. **Shot zones can be looked up from the wrong half of the court.** In
   `shoot`, probabilities are chosen by patch colour without checking which half
   belongs to the shooter ([L555-559](../code/hothand_version8.nlogo3d#L555-L559)).
   A shot forced by the shot clock from the backcourt can be scored at the
   opposite key's percentage.
3. **The three-point flag can carry over.** `three_pointer` is a global that
   `shoot` only ever sets to true, so a shot's point value can depend on an
   earlier evaluation.
4. **Possession tracking is fragile.** The `home_poss` flag is flipped in many
   places, and the guard `if ch > 1 [stop]`
   ([L266-267](../code/hothand_version8.nlogo3d#L266-L267)) and "bug fix
   August 28" comments suggest two players have sometimes held the ball at once.
5. **The model description is a blank template.** The Info tab's sections are
   still empty; documentation is only in `docs/ODD_basketball.pdf`.

---

## 7. Assumptions we introduced

These values are our own choices, not taken from Oldham or from data. They
should be stated in the report and, where possible, tested with alternative
values.

| Assumption | Value | Where |
|---|---|---|
| How often each zone comes up (restricted / key / mid / three) | 15 / 20 / 25 / 40% | `ZONE_WEIGHTS` |
| Prior strength | 3 average attempts | `Strategy.prior_strength` |
| Pass margin | 0.2 expected points | `Strategy.pass_margin` |
| Time to bring the ball up | 4–8 s | `GameConfig.setup_time` |
| Time per pass | 2–4 s | `GameConfig.pass_time` |
| Shot clock after an offensive rebound | 14 s (current NBA rule) | `GameConfig.offensive_rebound_clock` |
| Forced shot below | 3 s | `GameConfig.must_shoot_below` |
| Extra turnovers at full pressure | +10 percentage points | `GameConfig.pressure_turnover_bonus` |
| Possessions per game | 100 | `GameConfig.possessions_per_game` |
| Agents know their own true skill | yes | `Strategy.know_own_skill` |
| Team weight in experiments | 1.0 and 0.6 | `experiments.py` → `TEAM_WEIGHTS` |
| Reciprocity starts fully trusting | (cooperations + 1) / (tests + 1) | `PlayerAgent.reciprocity()` |
| Every agent sees every shot | yes | `environment.py` → `_shoot()` |
| Cold run length / exclusion window | 3 misses / 20 possessions | `GameConfig.cold_run_length`, `recovery_window` |

---

## 8. What this means when comparing results

- **Our results are not directly comparable to Oldham's.** He reports full-game
  scores between two teams; we report one team's points per possession and
  exclusion measures.
- **Scoring is higher than real basketball** (~1.3 points per possession with
  no pressure, versus ~1.1 in the NBA). Defensive pressure 0.15 gives realistic
  values.
- **There are fewer passes than real basketball** (~0.5 per possession). Only
  passes that decide who shoots are modelled, not ball movement around the
  perimeter.
- **Our conclusions are about the decision mechanism,** meaning how memory and
  exploration shape trust, not about predicting real game statistics.

These simplifications are deliberate: they remove the factors that would
otherwise make it impossible to attribute exclusion to memory.
