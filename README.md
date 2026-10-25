# When Teammates Stop Passing: Trust and Cooperation in Basketball

Multiagent systems course project. We study how the length of teammates'
memory affects passing and scoring, whether occasionally passing to
overlooked players prevents lasting exclusion after a run of misses, and
which of these strategies are stable when players are partly self-interested.

The model is a repeated Pass-or-Hog game with incomplete information about
teammates' skill. See [trust_model/GAME_THEORY.md](trust_model/GAME_THEORY.md).

## Repository layout

| Path | What it is |
|---|---|
| [`trust_model/`](trust_model/) | **Our model**: a possession-level Python simulation. Start with its [README](trust_model/README.md). |
| `code/hothand_version8.nlogo3d` | Reference model: Matthew Oldham's NetLogo 3D basketball simulation |
| `docs/ODD_basketball.pdf` | Oldham's ODD description of the reference model |
| `LICENSE`, `CITATION.cff`, `codemeta.json` | License and citation metadata for Oldham's model |

## Quick start

```bash
python3 -m trust_model.stage_game               # two-player game solved exactly
python3 -m trust_model.demo                     # one game, play by play
python3 -m trust_model.experiments --games 200  # whole-team strategies (~2.5 min)
python3 -m trust_model.metagame                 # mixed teams: equilibria (~1 min)
python3 -m trust_model.viz                      # visualiser in the browser (localhost:8000)
```

## Reference model

Oldham, M. (2019). *Drafting agent-based modeling into basketball analytics*
(Version 1.0.0). CoMSES Net.
https://www.comses.net/codebases/ed88c9b6-b54e-42c8-b7ae-c16a66dec57f/releases/1.0.0/
Released under the MIT License (see `LICENSE`).
