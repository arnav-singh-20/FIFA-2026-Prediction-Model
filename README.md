# World Cup 26 — Prediction Model

An interactive, single-page prediction tool for the FIFA World Cup 2026. It rates every team, predicts head-to-head matchups, simulates the rest of the bracket thousands of times, and projects individual awards — all client-side, no backend required.

**[Live demo →](wc2026_predictor.html)** 

> The scoring model started life as a small Python prototype (`wc2026_predictor.py`) and has since been ported into the vanilla JavaScript that powers this page, so the site works from a single `index.html` file with no server or build step. The math described below is identical in both versions.

---

## How the prediction model works

The model is intentionally simple and transparent — three ingredients, one formula, one simulation loop.

### 1. Power rating (Elo-style)

Every team gets a single number, a **power rating**, built from results already on the board:

```
rating(team) = 1500
             + 40 × group_stage_points
             + 15 × group_stage_goal_difference
             + 90 × knockout_wins
             + manual_form_adjustment
```

| Input | What it captures | Weight |
|---|---|---|
| `group_pts` | Points earned in the group stage (3 for a win, 1 for a draw) | ×40 |
| `group_gd` | Goal difference across the group stage | ×15 |
| `ko_wins` | Knockout rounds won so far (Round of 32 → Final) | ×90 |
| `adj` | A manual "current form" nudge (talent depth, injuries, momentum, home advantage, etc.) | ×1 |

1500 is the baseline rating every team starts from, the same convention chess and Elo-style sports models use. Knockout wins are weighted far more heavily than group-stage form (×90 vs ×40/×15) because surviving a single-elimination match against another World Cup team is a much stronger signal than group-stage results against uneven opposition.

The `adj` term is the one deliberately subjective input — it's where things a scoreline can't fully capture (a talisman returning from injury, a team peaking at the right time, historical big-game pedigree) get folded in by the model's maintainer.

### 2. Win probability (logistic / Elo formula)

Given two ratings, the classic Elo win-probability formula converts the rating gap into a probability:

```
P(A beats B) = 1 / (1 + 10^((rating_B − rating_A) / 400))
```

This is the same logistic curve used by chess Elo, FiveThirtyEight's sports models, and most Elo-derived football rating systems. A 400-point rating gap works out to roughly a 91%–9% favorite; a 100-point gap is close to 64%–36%. It's symmetric, bounded between 0 and 1, and never assigns a team a 0% or 100% chance, which keeps single-match upsets mathematically possible however lopsided the ratings.

### 3. Monte Carlo bracket simulation

Individual matchups are useful, but the **title odds** come from simulating the entire remaining bracket over and over:

1. For each unplayed tie, draw a random winner using that tie's win probability from step 2 (a weighted coin flip, not just "pick the favorite").
2. Advance the winners through the bracket exactly as the real tournament would — quarterfinals → semifinals → final.
3. Record the champion.
4. Repeat **20,000 times** and tally how often each team wins it all.

```
title_odds(team) = (times team won across all simulations) / 20,000
```

Running thousands of randomized brackets, rather than just chaining together the single most-likely winner of each round, is what turns a set of pairwise probabilities into realistic tournament-winning odds — it naturally accounts for a strong team needing to survive *multiple* uncertain matches in a row, not just one.

### 4. Confirmed results override the model

As real results come in, the model treats them as ground truth rather than just another simulated coin flip:

- Confirming a quarterfinal, semifinal, or the final locks that team's advancement to **100%** for every future simulation and bumps their `ko_wins`, which also lifts their power rating for any *remaining* hypothetical matchups.
- The bracket view, title odds, and honors sections all recompute instantly from the same underlying functions — there's no separate "results mode," the confirmed picks just constrain the same simulation.

### 5. Individual awards

Golden Boot, Golden Glove, Dark Horse, Champion, and Runner-Up are **not** derived from the rating formula — they're set directly (goals/clean-sheets/narrative reasoning don't feed into a single quantitative model here). Champion and Runner-Up do auto-fill once you confirm the actual final result, since those follow directly from the bracket.

---

## Project structure

```
index.html   → everything: markup, styling, and the prediction engine (self-contained, no build step)
```

Everything runs in the browser. Open `index.html` directly, or serve the folder with any static file server.

### Key functions (in `index.html`'s `<script>` block)

| Function | Purpose |
|---|---|
| `rating(team)` | Computes a team's power rating from `TEAMS[team]` |
| `winProbability(a, b)` | Returns `[P(a wins), P(b wins)]` using the Elo logistic formula |
| `simMatch(a, b)` | Simulates one randomized match outcome |
| `simulateBracket(nSims)` | Runs the full Monte Carlo simulation and returns title odds per team |
| `buildBracket()` | Renders the projected/confirmed path to the final |
| `buildOdds()` | Renders the title-odds bars from `simulateBracket()` |
| `TEAMS` | The data table of every team's `group_pts`, `group_gd`, `ko_wins`, and `adj` |
| `CONFIRMED` | Tracks which real-world results have been locked in |

---

## Updating the model

Everything a maintainer needs to touch lives near the top of the script:

- **`AWARDS`** — the predicted Golden Boot, Golden Glove, Champion, Runner-Up, and Dark Horse picks, with a one-line rationale for each.
- **`TEAMS`** — add, remove, or re-rate any team by editing its `group_pts`, `group_gd`, `ko_wins`, and `adj` values.
- **`CONFIRMED`** — normally set through the UI (the "confirm result" buttons), but can be pre-populated here too.

No build step, no dependencies — edit the values and refresh the page.

---

## Limitations

- Ratings are a simplified Elo variant, not a full statistical model (no expected goals, no player-level data, no bookmaker-odds blending).
- The `adj` (form) term is a manual, subjective input by design — it is the model's one deliberately human judgment call.
- 20,000 simulations is enough for title-odds percentages to be stable to roughly ±0.5–1%, not perfectly deterministic — refreshing the page will shift the long-tail (low-probability) teams slightly.
- Built for entertainment and illustration of Elo/Monte Carlo methodology — **not betting advice.**

---

## License

Add a license of your choice (MIT is a common default for small personal projects like this).
