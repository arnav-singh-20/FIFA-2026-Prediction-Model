"""
FIFA World Cup 2026 Prediction Model
=====================================

A power-rating model that turns each team's tournament performance so far
(group-stage points, goal difference, and how far they've advanced in the
knockouts) into a single "Power Rating" using an Elo-style scale, then
converts any two ratings into a win/draw/loss probability using the
standard logistic Elo formula.

DATA CUTOFF: through the Quarterfinal round, July 11, 2026.
Norway vs England and Argentina vs Switzerland quarterfinals had not yet
been played/finished as of the data cutoff, so those teams are rated on
their Round-of-16 form only.

METHODOLOGY (transparent, so you can tweak it):
  rating = 1500                              (baseline for any WC team)
          + 40  * group-stage points  (0-9)
          + 15  * group-stage goal difference
          + 90  * knockout wins so far (R32, R16, QF, SF each count once)
          + form/quality adjustment (small, judgment-based tweak for
            things a point table can't see: squad depth, key injuries,
            momentum, star-player form)

This is intentionally simple and auditable rather than a black box -
every number in a team's rating can be traced back to the group table
or the bracket.

Usage:
    python predictor.py                 # interactive: pick 2 teams
    python predictor.py France Spain    # one-off comparison
    python predictor.py --bracket       # simulate the rest of the bracket
    python predictor.py --list          # show full ratings table
"""

import sys
import random
import argparse

# ---------------------------------------------------------------------------
# 1. TEAM DATABASE
#    group_pts / group_gd / knockout_wins come from the actual 2026 group
#    tables and knockout results through the quarterfinal round.
#    adj is a small manual adjustment for squad quality / momentum / form
#    that a raw points table can't capture (e.g. Haaland's scoring streak,
#    France's attacking depth, injury news).
# ---------------------------------------------------------------------------

TEAMS = {
    # --- Still alive (as of data cutoff, QF stage) ---
    "France":       dict(group_pts=9, group_gd=8,  ko_wins=3, adj=90,
                          note="Unbeaten, 16-2 goal difference, 3 straight KO clean sheets, Mbappe/Dembele/Olise all scoring"),
    "Spain":        dict(group_pts=7, group_gd=6,  ko_wins=3, adj=70,
                          note="36-game unbeaten run, 0 goals conceded through 5 matches, elite possession control"),
    "Argentina":    dict(group_pts=9, group_gd=7,  ko_wins=2, adj=55,
                          note="Defending champions, Messi in vintage form, needed a dramatic comeback vs Egypt"),
    "England":      dict(group_pts=7, group_gd=4,  ko_wins=2, adj=45,
                          note="Bellingham brace + Kane goal beat Mexico away; defense has looked porous at times"),
    "Norway":       dict(group_pts=6, group_gd=1,  ko_wins=2, adj=55,
                          note="Haaland scoring in 14 straight internationals; upset Brazil in R16; first ever WC quarterfinal"),
    "Switzerland":  dict(group_pts=7, group_gd=5,  ko_wins=2, adj=20,
                          note="Disciplined, penalty-shootout specialists, lower ceiling attacking output"),

    # --- Eliminated in the Quarterfinals ---
    "Morocco":      dict(group_pts=7, group_gd=4,  ko_wins=2, adj=30,
                          note="Back-to-back deep runs, Bounou excellent, lost 0-2 to France"),
    "Belgium":      dict(group_pts=6, group_gd=3,  ko_wins=2, adj=10,
                          note="Golden generation's last dance, lost narrowly 1-2 to Spain"),

    # --- Eliminated in the Round of 16 ---
    "Brazil":       dict(group_pts=7, group_gd=5,  ko_wins=1, adj=40,
                          note="Talented squad but shocked 1-2 by Norway/Haaland"),
    "Portugal":     dict(group_pts=5, group_gd=5,  ko_wins=1, adj=15,
                          note="Ronaldo's last World Cup ended 0-1 to Spain"),
    "Colombia":     dict(group_pts=7, group_gd=3,  ko_wins=1, adj=5,
                          note="Lost R16 penalty shootout to Switzerland"),
    "Netherlands":  dict(group_pts=6, group_gd=3,  ko_wins=1, adj=10),
    "Germany":      dict(group_pts=6, group_gd=6,  ko_wins=1, adj=15,
                          note="Blew out Curacao 7-1 in groups but fell to Paraguay in R16"),
    "Paraguay":     dict(group_pts=4, group_gd=0,  ko_wins=2, adj=0,
                          note="Beat Germany on penalties, lost narrowly to France"),
    "Mexico":       dict(group_pts=9, group_gd=4,  ko_wins=1, adj=-10,
                          note="Co-host, lost a thriller 2-3 to England despite a red card advantage"),
    "USA":          dict(group_pts=6, group_gd=2,  ko_wins=1, adj=-10,
                          note="Co-host, eliminated by Belgium in R16"),
    "Canada":       dict(group_pts=4, group_gd=4,  ko_wins=1, adj=-15,
                          note="Co-host, lost 0-3 to Morocco"),
    "Egypt":        dict(group_pts=4, group_gd=-1, ko_wins=1, adj=20,
                          note="Salah-inspired, lost a wild 2-3 comeback to Argentina"),
    "CapeVerde":    dict(group_pts=5, group_gd=2,  ko_wins=1, adj=15,
                          note="Tournament's feel-good story, eliminated by Argentina in extra time"),
    "Croatia":      dict(group_pts=6, group_gd=0,  ko_wins=1, adj=0),
    "Ivory Coast":  dict(group_pts=4, group_gd=1,  ko_wins=1, adj=0),

    # --- Eliminated in the Round of 32 or Group Stage ---
    "Uruguay":      dict(group_pts=6, group_gd=2,  ko_wins=0, adj=10),
    "Ecuador":      dict(group_pts=5, group_gd=1,  ko_wins=0, adj=0),
    "Senegal":      dict(group_pts=3, group_gd=2,  ko_wins=0, adj=5),
    "Japan":        dict(group_pts=5, group_gd=1,  ko_wins=0, adj=0),
    "Ghana":        dict(group_pts=4, group_gd=-1, ko_wins=0, adj=0),
    "DR Congo":     dict(group_pts=4, group_gd=1,  ko_wins=0, adj=-5),
    "Sweden":       dict(group_pts=4, group_gd=1,  ko_wins=0, adj=0),
    "Algeria":      dict(group_pts=4, group_gd=-2, ko_wins=0, adj=-5),
    "Australia":    dict(group_pts=3, group_gd=-1, ko_wins=0, adj=-10),
    "Panama":       dict(group_pts=0, group_gd=-3, ko_wins=0, adj=-15),
    "South Africa": dict(group_pts=4, group_gd=-1, ko_wins=0, adj=-10),
    "Korea Republic": dict(group_pts=3, group_gd=-1, ko_wins=0, adj=-10),
    "Czechia":      dict(group_pts=1, group_gd=-4, ko_wins=0, adj=-15),
    "Bosnia and Herzegovina": dict(group_pts=4, group_gd=-1, ko_wins=0, adj=-15),
    "Qatar":        dict(group_pts=1, group_gd=-8, ko_wins=0, adj=-20),
    "Iraq":         dict(group_pts=0, group_gd=-11,ko_wins=0, adj=-25),
    "Jordan":       dict(group_pts=0, group_gd=-5, ko_wins=0, adj=-25),
    "Austria":      dict(group_pts=4, group_gd=0,  ko_wins=0, adj=-5),
    "Uzbekistan":   dict(group_pts=0, group_gd=-9, ko_wins=0, adj=-25),
}


def rating(team: str) -> float:
    """Compute a team's Elo-style power rating."""
    key = _resolve(team)
    t = TEAMS[key]
    return (1500
            + 40 * t["group_pts"]
            + 15 * t["group_gd"]
            + 90 * t["ko_wins"]
            + t["adj"])


def _resolve(name: str) -> str:
    """Case-insensitive / fuzzy team-name lookup."""
    name_l = name.strip().lower()
    for k in TEAMS:
        if k.lower() == name_l:
            return k
    matches = [k for k in TEAMS if name_l in k.lower()]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Unknown or ambiguous team: '{name}'. "
                    f"Try one of: {', '.join(sorted(TEAMS))}")


def win_probability(team_a: str, team_b: str):
    """Standard Elo logistic formula -> probability team_a beats team_b
    in a match with no draws allowed (knockout, so a draw becomes a coin
    flip weighted by rating, mimicking extra time / penalties)."""
    ra, rb = rating(team_a), rating(team_b)
    p_a = 1 / (1 + 10 ** ((rb - ra) / 400))
    return p_a, 1 - p_a


def predict_match(team_a: str, team_b: str):
    a, b = _resolve(team_a), _resolve(team_b)
    p_a, p_b = win_probability(a, b)
    ra, rb = rating(a), rating(b)
    winner = a if p_a >= p_b else b
    return {
        "team_a": a, "team_b": b,
        "rating_a": round(ra), "rating_b": round(rb),
        "prob_a": p_a, "prob_b": p_b,
        "predicted_winner": winner,
        "confidence": max(p_a, p_b),
    }


def print_prediction(team_a: str, team_b: str):
    r = predict_match(team_a, team_b)
    print(f"\n{r['team_a']} ({r['rating_a']}) vs {r['team_b']} ({r['rating_b']})")
    print(f"  {r['team_a']}: {r['prob_a']*100:5.1f}%")
    print(f"  {r['team_b']}: {r['prob_b']*100:5.1f}%")
    print(f"  --> Predicted winner: {r['predicted_winner']} "
          f"({r['confidence']*100:.1f}% confidence)\n")


def list_ratings():
    ranked = sorted(TEAMS, key=rating, reverse=True)
    print(f"\n{'Team':<26}{'Rating':>8}")
    print("-" * 34)
    for t in ranked:
        print(f"{t:<26}{round(rating(t)):>8}")
    print()


def simulate_bracket(n_sims: int = 20000):
    """Monte Carlo simulation of the known remaining bracket:
       SF1: France vs Spain
       SF2: winner(Norway,England) vs winner(Argentina,Switzerland)
       Final: winner(SF1) vs winner(SF2)
    """
    def sim_match(a, b):
        pa, pb = win_probability(a, b)
        return a if random.random() < pa else b

    titles = {t: 0 for t in TEAMS}
    for _ in range(n_sims):
        sf2a = sim_match("Norway", "England")
        sf2b = sim_match("Argentina", "Switzerland")
        f1 = sim_match("France", "Spain")
        f2 = sim_match(sf2a, sf2b)
        champ = sim_match(f1, f2)
        titles[champ] += 1

    ranked = sorted(titles.items(), key=lambda x: x[1], reverse=True)
    print(f"\nMonte Carlo bracket simulation ({n_sims:,} runs)")
    print(f"{'Team':<15}{'Title %':>10}")
    print("-" * 25)
    for team, count in ranked:
        if count > 0:
            print(f"{team:<15}{count / n_sims * 100:>9.1f}%")
    print()


def interactive():
    print("=== FIFA World Cup 2026 Predictor ===")
    print("Type two team names (or 'list' to see all teams, 'quit' to exit)\n")
    while True:
        a = input("Team A: ").strip()
        if a.lower() == "quit":
            break
        if a.lower() == "list":
            list_ratings()
            continue
        b = input("Team B: ").strip()
        try:
            print_prediction(a, b)
        except KeyError as e:
            print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 Predictor")
    parser.add_argument("teams", nargs="*", help="Two team names to compare")
    parser.add_argument("--list", action="store_true", help="Show full ratings table")
    parser.add_argument("--bracket", action="store_true", help="Simulate the rest of the bracket")
    args = parser.parse_args()

    if args.list:
        list_ratings()
    elif args.bracket:
        simulate_bracket()
    elif len(args.teams) == 2:
        print_prediction(*args.teams)
    else:
        interactive()
