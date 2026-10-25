"""The two-player Pass-or-Hog stage game, solved exactly (GAME_THEORY.md, layer 1).

Each of two teammates gets the ball once. The holder has an okay look worth s
expected points; the teammate has a better look worth b > s. The holder
either passes (teammate takes the better look) or hogs (shoots the okay look).

    u_i = lam * team points + (1 - lam) * (own points + a * points set up by own passes)

    python3 -m trust_model.stage_game                      # s=0.9, b=1.3, lam=0.6
    python3 -m trust_model.stage_game --s 0.9 --b 1.3 --lam 0.8 --a 0.25
"""
import argparse

ACTIONS = ("Pass", "Hog")


def payoffs(s, b, lam, a=0.0):
    """Row player's payoff for (my action, teammate's action)."""
    def u(team, own, assisted):
        return lam * team + (1 - lam) * (own + a * assisted)

    return {
        ("Pass", "Pass"): u(2 * b, b, b),   # R: both get the better look
        ("Pass", "Hog"): u(b + s, 0, b),    # S: I set you up, you hog
        ("Hog", "Pass"): u(s + b, s + b, 0),  # T: I shoot, and you set me up
        ("Hog", "Hog"): u(2 * s, s, 0),     # P: both take the worse look
    }


def pure_nash(table):
    """Symmetric 2x2 game: (x, y) is Nash if neither player gains by switching."""
    other = {"Pass": "Hog", "Hog": "Pass"}
    eq = []
    for x in ACTIONS:
        for y in ACTIONS:
            if table[(x, y)] >= table[(other[x], y)] and table[(y, x)] >= table[(other[y], x)]:
                eq.append((x, y))
    return eq


def dilemma_threshold(s, b, a=0.0):
    """Hog strictly dominates Pass exactly when lam < this value."""
    # Hog beats Pass on my own possession iff s > b * (lam + (1 - lam) * a)
    return (s / b - a) / (1 - a) if a < 1 else float("-inf")


def grim_trigger_patience(s, b, lam, a=0.0):
    """Smallest continuation probability delta at which grim trigger sustains
    mutual passing in the infinitely repeated game: (T - R) / (T - P)."""
    t = payoffs(s, b, lam, a)
    T, R, P = t[("Hog", "Pass")], t[("Pass", "Pass")], t[("Hog", "Hog")]
    if T <= R:
        return 0.0  # passing is already individually best
    return (T - R) / (T - P)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--s", type=float, default=0.9, help="value of the holder's okay look")
    parser.add_argument("--b", type=float, default=1.3, help="value of the teammate's better look")
    parser.add_argument("--lam", type=float, default=0.6, help="team weight lambda")
    parser.add_argument("--a", type=float, default=0.0, help="assist credit")
    args = parser.parse_args()
    s, b, lam, a = args.s, args.b, args.lam, args.a

    t = payoffs(s, b, lam, a)
    print(f"s = {s}, b = {b}, lambda = {lam}, assist credit = {a}\n")
    print("Payoffs (me, teammate):")
    print(f"{'':12}{'teammate Pass':>18}{'teammate Hog':>18}")
    for x in ACTIONS:
        cells = "".join(f"{f'({t[(x, y)]:.2f}, {t[(y, x)]:.2f})':>18}" for y in ACTIONS)
        print(f"{'I ' + x:12}{cells}")

    T, R, P, S = t[("Hog", "Pass")], t[("Pass", "Pass")], t[("Hog", "Hog")], t[("Pass", "Hog")]
    print(f"\nT = {T:.3f}  R = {R:.3f}  P = {P:.3f}  S = {S:.3f}")
    print(f"Prisoner's Dilemma (T > R > P > S): {T > R > P > S}")
    print(f"Hog dominates whenever lambda < {dilemma_threshold(s, b, a):.3f}")
    print(f"Nash equilibria: {pure_nash(t)}")
    print(f"Team optimum: (Pass, Pass), {2 * b:.2f} team points vs {2 * s:.2f} if both hog "
          f"(price of anarchy {b / s:.2f})" if T > R else "Team optimum (Pass, Pass) is also the equilibrium.")
    d = grim_trigger_patience(s, b, lam, a)
    print(f"Repeated game: grim trigger sustains passing if continuation probability >= {d:.3f}")
    if a == 0 and T > R:
        print(f"Mechanism design: an assist credit of at least {(s / b - lam) / (1 - lam):.3f} removes the dilemma")


if __name__ == "__main__":
    main()
