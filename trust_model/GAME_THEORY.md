# The game-theoretic foundation of trust_model

This document explains how our model is built on game theory: what the game
is, how it is analysed, how each part maps onto the code, and what the results
so far show.

**Contents**
1. [Why game theory](#1-why-game-theory)
2. [The game](#2-the-game)
3. [Layer 1: the stage game (solved analytically)](#3-layer-1-the-stage-game)
4. [Layer 2: the repeated game with incomplete information and noise (simulated)](#4-layer-2-the-repeated-game)
5. [Layer 3: the meta-game (empirical game-theoretic analysis)](#5-layer-3-the-meta-game)
6. [Results so far](#6-results-so-far)
7. [Research question and hypotheses](#7-research-question-and-hypotheses)
8. [Where each concept lives in the code](#8-where-each-concept-lives-in-the-code)
9. [Limitations](#9-limitations)
10. [References](#10-references)

---

## 1. Why game theory

A **game** is a situation in which each player's best choice depends on what
the other players do. Game theory becomes interesting when players' interests
are at least partly in conflict.

Our first version of the model was a **learning model**. All five players
shared one goal, team points, and each passer's only problem was estimating
teammates' skill: a multi-armed bandit. In game-theory terms that is a
*common-interest* (team) game, the trivial case. Nobody has a reason to act
against anybody else, so there are no strategic trade-offs to analyse.

Real players care about the team **and** about themselves: their points, stats
and contracts. Giving each player a payoff that mixes the two turns the
possession into a genuine game. Passing becomes a personal sacrifice, and
whether a player passes depends on whether they expect teammates to pass back.
That is the question of **cooperation**, which is central to game theory.

The learning model is not discarded. It is the special case λ = 1 (Section 2),
and it remains the right tool for the *skill-belief* part of the problem.

---

## 2. The game

| Element | In our model |
|---|---|
| **Players** | 5 teammates, *N* = {0, 1, 2, 3, 4} |
| **Types** (private, unobserved) | Each player's true shooting skill θᵢ (e.g. 1.25 = 25% better than average). Agents never see anyone's θ except their own. |
| **Actions** at each decision | Shoot, or pass to teammate *j* |
| **Moves of nature** | Which shot zone each player's open look comes from; whether shots go in; steals; rebounds |
| **Information** | Everyone sees every look, every pass and every shot result, but not true skills |
| **Repetition** | 100 possessions per game with the same five players |
| **Payoffs** | See below |

### Payoffs

Each player *i* receives

> **uᵢ = λ · (team points) + (1 − λ) · (own points + a · assisted points)**

- **λ (team weight)** is how much a player cares about the team versus themselves.
  - λ = 1: fully team-first. Everyone wants the same thing.
  - λ < 1: partly selfish.
- **a (assist credit)** is how much personal credit a player gets for points they
  set up with a pass. It's 0 by default. A coach or league can change it (see the
  mechanism-design note in 3.4).

λ and *a* belong to the **game** (`GameConfig.team_weight`, `GameConfig.assist_credit`).
They are the same for every player, so the game is symmetric. What differs between
players is their **strategy**, meaning the rule they use to decide.

---

## 3. Layer 1: the stage game

The simplest version of the problem, solved by hand. The calculator is
`python3 -m trust_model.stage_game`.

### 3.1 Set-up

Two teammates, A and B. Each gets the ball once.

- The holder has an **okay look** worth *s* expected points.
- The teammate has a **better look** worth *b* > *s*.
- The holder chooses **Pass** (the teammate takes the better look) or **Hog**
  (the holder shoots the okay look).

### 3.2 Payoffs

Work out A's payoff for each pair of choices (with *a* = 0):

| A's choice | B's choice | Team points | A's own points | A's payoff | Name |
|---|---|---|---|---|---|
| Pass | Pass | 2b | b (B set A up) | 2λb + (1−λ)b = **b(1 + λ)** | R (reward) |
| Pass | Hog | b + s | 0 | **λ(b + s)** | S (sucker) |
| Hog | Pass | s + b | s + b | **s + b** | T (temptation) |
| Hog | Hog | 2s | s | 2λs + (1−λ)s = **s(1 + λ)** | P (punishment) |

As a matrix (A's payoff, B's payoff):

| | B passes | B hogs |
|---|---|---|
| **A passes** | R, R | S, T |
| **A hogs** | T, S | P, P |

### 3.3 When it is a Prisoner's Dilemma

A symmetric 2 × 2 game is a **Prisoner's Dilemma** when T > R > P > S.

- **T > R:** s + b > b + λb ⟺ **s > λb**
- **R > P:** b(1 + λ) > s(1 + λ) ⟺ b > s, always true
- **P > S:** s + λs > λb + λs ⟺ **s > λb**

Both conditions that matter reduce to the same inequality:

> **The possession is a Prisoner's Dilemma exactly when λ < s / b.**

In that case:
- **Hog strictly dominates Pass.** Whatever the teammate does, hogging pays more.
- The **unique Nash equilibrium is (Hog, Hog)**.
- **Both players would be better off at (Pass, Pass)**: R > P. The equilibrium is
  inefficient. The team scores 2s instead of 2b, so the **price of anarchy** (optimal
  team points ÷ equilibrium team points) is b / s.

When λ > s / b, Pass dominates and the only equilibrium is (Pass, Pass), which is
also team-optimal. There is no dilemma.

**Example** (the calculator's defaults): s = 0.9, b = 1.3, λ = 0.6.

| | B passes | B hogs |
|---|---|---|
| **A passes** | 2.08, 2.08 | 1.32, 2.20 |
| **A hogs** | 2.20, 1.32 | 1.44, 1.44 |

T = 2.20 > R = 2.08 > P = 1.44 > S = 1.32, so it is a Prisoner's Dilemma. The
threshold is s / b = 0.692, so any team weight below 69% creates the dilemma. The
price of anarchy is 1.44.

**What this means for basketball:** the dilemma is strongest when the teammate's
look is only *somewhat* better than the holder's (s / b close to 1). When the
teammate is wide open at the rim and the holder has a bad shot (s / b small), even
a fairly selfish player passes.

### 3.4 Mechanism design: assist credit

With assist credit *a*, passing earns the passer (1 − λ)·a·b personally. Hog
then dominates only when

> s > b · (λ + (1 − λ) a)

so the dilemma disappears once

> **a ≥ (s / b − λ) / (1 − λ)**

In the example, an assist credit of **0.231** (roughly: a player values an assist
at a quarter of a basket of their own) removes the dilemma. This connects to the
course's **mechanism design** module: a coach or league can choose the reward
scheme so that individually rational play becomes team-optimal.

### 3.5 Repeating the stage game

If the game is repeated and after each round it continues with probability δ,
mutual passing can be sustained by **grim trigger** ("I pass until you hog, then
I hog forever") whenever

> **δ ≥ (T − R) / (T − P)**

In the example, δ ≥ 0.158. This is a standard **folk theorem** result: repetition
lets patient players cooperate even when a single round would not.

Two complications push us to simulation:

1. **Our game has a known end** (100 possessions). In a finitely repeated
   Prisoner's Dilemma, backward induction gives the unique subgame-perfect
   equilibrium "hog every time". Cooperation in practice therefore depends on
   players using simple rules (memory-based strategies) rather than full
   backward induction. That is what we model.
2. **Noise.** Grim trigger and tit-for-tat are known to break down when
   players can misread each other (Wu & Axelrod, 1995). Our model contains
   exactly that kind of noise, described next.

---

## 4. Layer 2: the repeated game

The full model, simulated. It adds three things to the stage game: five
players, **incomplete information** about skill, and **noise** from shot
outcomes.

### 4.1 Incomplete information: a Bayesian game

Each player's true skill θᵢ is a **type** that others cannot see, which
makes this a Bayesian game (Harsanyi, 1967). Agents form beliefs about
types from what they observe:

> **θ̂ⱼ = (makes + prior) / (expected makes + prior)**, over the last *k* shots by *j*

Agents know their own type (`know_own_skill=True`).

### 4.2 Where the noise comes from

The key mechanism is an **information asymmetry**:

1. A good shooter (P2, θ = 1.25) misses three shots by chance.
2. Teammates' estimate θ̂₂ drops (to about 0.57). Passing to P2 now looks
   worse than shooting, so **they stop passing to P2. In their eyes this is
   not defection.**
3. P2 knows they are good. In P2's eyes, teammates are taking worse shots when
   P2 is open with a better one. **To P2 this is defection.**
4. If P2 reciprocates, P2 stops passing.
5. Teammates now see P2 hogging, which really is defection in their view, so
   they reciprocate too.

An unlucky streak gets misread as non-cooperation, and the misreading spreads.
That is the "when teammates stop passing" spiral in game-theory terms.

### 4.3 What counts as cooperation and defection

Each agent judges every teammate's decision (`agents.py` → `observe_decision`).

- A decision is a **test of cooperation** if, by the observer's own beliefs,
  passing would have given the team at least `pass_margin` (0.2) more expected
  points than shooting.
- In a test, **passing = cooperate** and **shooting = defect**.
- Other decisions (when shooting was fine) aren't judged.

Every agent applies this to its own beliefs, which can be wrong. This is
what lets the misreading in 4.2 happen.

Separately, the environment records an **objective** version of the same test
using true skills. That gives the **cooperation rate** measure (Section 8).

### 4.4 Strategies

A strategy has three parts: **memory length**, **cooperation rule** and
**forgiveness**.

**Cooperation rule** (`Strategy.cooperation`). A pass to *j* is valued at

> **wᵢⱼ × (1 − turnover chance) × θ̂ⱼ × (look's make chance) × points**

while shooting is valued at the holder's own expected points (which count both
for the team and for the holder). The weight wᵢⱼ ranges from the selfish value
**λ + (1 − λ)a** to **1** (team-first):

| Rule | wᵢⱼ | Game-theory name |
|---|---|---|
| `always` | 1 | Unconditional cooperator (ALLC) |
| `never` | λ + (1 − λ)a: the myopic best response to the stage game | Always defect (ALLD) |
| `reciprocal` | between the two, in proportion to how often *j* has cooperated in its last *k* tests | Memory-*k* tit-for-tat |

A reciprocator's trust in *j* is (cooperations + 1) ÷ (tests + 1), so it starts
fully trusting ("cooperate first", as in tit-for-tat) and falls with each
defection it remembers. Reciprocity is **personal**: a player can keep passing
to cooperative teammates and freeze out a hog.

**Memory length *k*** (`Strategy.memory_length`) applies both to skill memory
(last *k* shots) and to cooperation memory (last *k* tests). Short memory
forgives quickly but also overreacts to streaks; long memory is stable but
holds grudges and old misses.

**Forgiveness** (`Strategy.exploration`): with probability ε, pass to the
teammate who has gone longest without a shot. This is the repeated-game
counterpart of **generous tit-for-tat** (Nowak & Sigmund, 1992): it breaks
cycles of retaliation by occasionally cooperating regardless of history. It
also gives frozen-out players new shots, so their skill estimates can recover.

### 4.5 The strategies in the code

| Name | Memory *k* | Cooperation | Forgiveness ε | Role |
|---|---|---|---|---|
| `short_memory` | 5 | always | 0 | ALLC, short memory |
| `long_memory` | 30 | always | 0 | ALLC, long memory |
| `short_memory_explore` | 5 | always | 0.10 | ALLC with forgiveness |
| `oracle` | knows true skills | always | 0 | Benchmark: team-optimal play |
| `hog` | 5 | never | 0 | ALLD |
| `reciprocator` | 5 | reciprocal | 0 | Tit-for-tat, short memory |
| `forgiving_reciprocator` | 5 | reciprocal | 0.10 | Generous tit-for-tat |
| `long_reciprocator` | 30 | reciprocal | 0 | Tit-for-tat, long memory |

**Sanity check built into the model:** at λ = 1 the selfish weight equals 1,
so `hog`, `reciprocator` and `short_memory` behave identically. The
simulation reproduces this exactly (Section 6).

---

## 5. Layer 3: the meta-game

Layer 2 tells us what happens when a whole team uses one strategy. Game
theory asks a sharper question: **would any player want to switch?** A
strategy that does well when everyone uses it can still be exploited by a
single deviator.

We answer this with **empirical game-theoretic analysis** (EGTA; Wellman,
2006). It treats each strategy as a single "move" in a larger game and
estimates that game's payoffs by simulation. Run it with
`python3 -m trust_model.metagame`.

### 5.1 Method

1. **Strategy set:** `short_memory` (ALLC), `hog` (ALLD), `reciprocator`,
   `forgiving_reciprocator`, `long_reciprocator`.
2. **Profiles:** every way of filling 5 seats from 5 strategies (order
   doesn't matter): **126 profiles**.
3. **Payoff table:** simulate each profile for many games. Strategies are
   shuffled across seats each game, so no strategy is tied to a skill level.
   Record each strategy's average payoff per possession, with its standard
   error.
4. **Nash check:** for each "everyone plays *s*" profile, would one player gain
   by switching to another strategy? If no switch helps, it is a **symmetric
   Nash equilibrium**.
5. **Replicator dynamics** (Taylor & Jonker, 1978): imagine a large population
   from which teams are drawn at random. Strategies that earn more than average
   spread; those that earn less shrink. The end state shows which strategies
   survive and from which starting mixes (the **basin of attraction**).

---

## 6. Results so far

Settings: equal skills, defensive pressure 0.15, 100 games per profile (meta-game)
or 200 games per cell (experiments). These are first-pass numbers. The payoff
differences are small, so final results should use more games (Section 9).

### 6.1 Whole-team strategies (`experiments.py`)

| Strategy | λ | Team pts/poss | Efficiency vs oracle | Cooperation rate | Cold players excluded |
|---|---|---|---|---|---|
| oracle | any | 1.130 | 1.000 | 1.00 | 15% |
| short_memory (ALLC) | any | 1.079 | 0.955 | 0.63 | 64% |
| long_memory (ALLC) | any | 1.102 | 0.975 | 0.72 | 43% |
| short_memory_explore | any | 1.075 | 0.951 | 0.69 | 30% |
| hog | 1.0 | 1.079 | 0.955 | 0.63 | 64% |
| hog | 0.6 | 1.016 | 0.900 | **0.08** | **98%** |
| reciprocator | 0.6 | 1.066 | 0.943 | 0.45 | 83% |
| forgiving_reciprocator | 0.6 | 1.055 | 0.934 | 0.55 | 43% |
| long_reciprocator | 0.6 | 1.067 | 0.945 | 0.57 | 59% |

**Readings:**
- **Two separate failures.** Even fully team-first players cooperate only 63% of
  the time when passing is truly better. That is the *learning* failure: wrong
  beliefs about skill. Selfish payoffs add a *strategic* failure on top: hogs
  drop to 8%.
- **The spiral is real.** Reciprocators start out cooperative, but misread
  slumps as defection and settle at 45%, well below ALLC's 63%.
- **Forgiveness cuts exclusion** among reciprocators (83% → 43%) but costs some
  points.
- **Long memory** cooperates more and excludes less than short memory, both for
  cooperators and for reciprocators.

### 6.2 The meta-game (`metagame.py`)

**λ = 1 (no dilemma).** `hog`, `reciprocator` and `short_memory` are identical, as
the theory predicts, so they are neutral to one another. The only real difference
is learning: `long_reciprocator` (long memory) earns the most, and forgiveness
costs a little because exploratory passes are sometimes poor shots.

**λ = 0.6 (a Prisoner's Dilemma in many possessions).**

| Everyone plays | Payoff/poss | Team pts/poss | Nash? |
|---|---|---|---|
| short_memory (ALLC) | 0.739 | 1.086 | **No**: a hog gains +0.025 |
| hog (ALLD) | 0.691 | 1.016 | **Yes** |
| reciprocator | 0.738 | 1.085 | **Yes** |
| forgiving_reciprocator | 0.713 | 1.048 | No: a plain reciprocator gains +0.022 |
| long_reciprocator | 0.728 | 1.071 | Borderline (within noise) |

Replicator dynamics: **hogs take over from every starting mix except one that is
60% reciprocators**, which ends with reciprocators taking over.

**λ = 0.4 (a stronger dilemma).** Hogs take over from **every** starting mix,
including 60% reciprocators.

**Readings:**
- **Unconditional cooperation is exploitable.** A team of team-first players is
  not stable once players are partly selfish: one hog does better.
- **Reciprocity creates a second, better equilibrium.** All-reciprocator is a Nash
  equilibrium with higher payoffs than all-hog (0.738 vs 0.691): the classic
  repeated-game result. But it needs a **critical mass** of reciprocators to
  establish itself, and it loses that support as λ falls.
- **Forgiveness helps the team but isn't individually stable.** Forgiving
  reciprocators reduce exclusion (6.1), but a player who drops the forgiveness
  does better. Forgiveness is a public good: every forgiving pass costs the
  passer and benefits the team.
- **This motivates mechanism design.** If teams benefit from forgiveness but
  individuals don't provide it, a reward scheme such as assist credit (3.4) is a
  natural next experiment.

---

## 7. Research question and hypotheses

The original question stays, with one addition for the game layer:

> How does the length of teammates' memory affect passing decisions and team
> scoring, can occasionally passing to overlooked players prevent lasting
> exclusion after a run of misses, **and which of these strategies are stable
> when players are partly self-interested?**

Hypotheses, each tested with the tools above:

| | Hypothesis | Test |
|---|---|---|
| H1 | Short memory produces more lasting exclusion than long memory after unlucky misses. | `experiments.py`: excluded_rate by strategy |
| H2 | Forgiveness (ε > 0) reduces exclusion and restores cooperation among reciprocators. | `experiments.py`: forgiving_reciprocator vs reciprocator |
| H3 | When λ < s/b, unconditional cooperation is not an equilibrium, while reciprocity can be. | `stage_game.py` (analytically); `metagame.py` (Nash check) |
| H4 | The basin of attraction of reciprocal cooperation shrinks as λ falls. | `metagame.py --team-weights 1.0 0.8 0.6 0.4` |
| H5 | Forgiveness is beneficial for the team but not individually stable, and enough assist credit can make it stable. | `metagame.py` with an assist-credit sweep (next step) |

---

## 8. Where each concept lives in the code

| Game-theory concept | Code |
|---|---|
| Players | `PlayerAgent` (`agents.py`), 5 per `Game` |
| Types (hidden skill) | `GameConfig.skills`; agents see only `estimated_skill()` |
| Payoff function uᵢ | `Game._score_utilities()` (`environment.py`) |
| λ and assist credit | `GameConfig.team_weight`, `GameConfig.assist_credit` |
| Selfish (myopic best-response) pass value | `GameConfig.selfish_pass_weight` |
| Strategy | `Strategy` (`config.py`) |
| Cooperation rule wᵢⱼ | `PlayerAgent.pass_weight()`, `cooperation_level()` |
| Judging cooperation / defection | `PlayerAgent.observe_decision()`, `reciprocity()` |
| Forgiveness (generous TFT) | `Strategy.exploration` in `PlayerAgent.decide()` |
| Belief updating | `PlayerAgent.observe_shot()`, `estimated_skill()` |
| Objective cooperation rate | `Game._truly_better_to_pass()`, `metrics.py` → `cooperation_rate` |
| Efficiency vs optimum | `experiments.py` → `efficiency_vs_oracle` |
| Stage game, Nash, PD threshold, folk theorem, assist-credit threshold | `stage_game.py` |
| Profiles, payoff table, Nash check, replicator dynamics | `metagame.py` |

Commands:

```bash
python3 -m trust_model.stage_game --s 0.9 --b 1.3 --lam 0.6      # layer 1
python3 -m trust_model.experiments --games 200                    # layer 2 (~2.5 min)
python3 -m trust_model.metagame --team-weights 1.0 0.6 0.4        # layer 3 (~1.5 min)
python3 -m trust_model.demo --team-weight 0.6 \
    --strategy hog,reciprocator,reciprocator,short_memory,forgiving_reciprocator
```

---

## 9. Limitations

1. **Small payoff differences.** Differences between strategies are a few
   hundredths of a point per possession, and some Nash checks fall within
   noise (marked `~Nash`). Final results should use more games per profile
   (e.g. `--games 500`).
2. **Reciprocity responds to the team's interest, not personal treatment.** A
   reciprocator judges whether a teammate passed when the *team* would have
   benefited, not whether they passed *to it* specifically.
3. **The stage game simplifies away turnovers and margins.** The analytical
   threshold λ < s/b ignores the turnover risk and the 0.2-point pass margin
   that the simulation includes. Both make passing slightly less attractive.
4. **Finite horizon.** With a known last possession, strict backward induction
   would predict hogging throughout. Our agents use memory-based rules instead,
   which is a modelling choice to state.
5. **Shared observation.** Every agent sees every look and shot. Partial
   observation would make beliefs differ more between agents and is a natural
   extension.
6. **The strategy set is small.** EGTA results only hold relative to the
   strategies included. Adding more (e.g. different ε or *k* values) can change
   which equilibria exist.

---

## 10. References

- Axelrod, R. (1984). *The Evolution of Cooperation*. Basic Books.
- Denrell, J., & March, J. G. (2001). Adaptation as information restriction: The hot stove effect. *Organization Science*, 12(5), 523–538.
- Fudenberg, D., & Maskin, E. (1986). The folk theorem in repeated games with discounting or with incomplete information. *Econometrica*, 54(3), 533–554.
- Harsanyi, J. C. (1967). Games with incomplete information played by "Bayesian" players, Part I. *Management Science*, 14(3), 159–182.
- Nowak, M. A., & Sigmund, K. (1992). Tit for tat in heterogeneous populations. *Nature*, 355, 250–253.
- Oldham, M. (2019). *Drafting agent-based modeling into basketball analytics* (Version 1.0.0). CoMSES Net.
- Taylor, P. D., & Jonker, L. B. (1978). Evolutionarily stable strategies and game dynamics. *Mathematical Biosciences*, 40(1–2), 145–156.
- Wellman, M. P. (2006). Methods for empirical game-theoretic analysis. *Proceedings of AAAI-06*, 1552–1555.
- Wu, J., & Axelrod, R. (1995). How to cope with noise in the iterated prisoner's dilemma. *Journal of Conflict Resolution*, 39(1), 183–189.
