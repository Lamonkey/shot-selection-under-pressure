"""League-wide (multi-season) clutch shot-selection analysis.

The single-series case study (2026 Finals) looked like a clean confirmation of
the pressure hypothesis. Pooling every playoff game 2016-2026 tests whether that
generalizes — and forces the score-state confound into the open.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

STATE_ORDER = ["Trailing 4+", "Trailing 1-3", "Tied", "Leading 1-3", "Leading 4+"]


def score_state(margin: int) -> str:
    """Bucket the pre-shot margin (shooter's team perspective)."""
    if margin <= -4:
        return "Trailing 4+"
    if margin < 0:
        return "Trailing 1-3"
    if margin == 0:
        return "Tied"
    if margin <= 3:
        return "Leading 1-3"
    return "Leading 4+"


def add_score_state(shots: pd.DataFrame) -> pd.DataFrame:
    df = shots.copy()
    df["state"] = pd.Categorical(
        df["margin_before"].apply(score_state), STATE_ORDER, ordered=True
    )
    return df


def _wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson interval for a proportion."""
    if n == 0:
        return (np.nan, np.nan)
    z = 1.96
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (center - half, center - half + 2 * half)


def three_rate_ci(sub: pd.DataFrame) -> dict:
    k, n = int(sub["is_three"].sum()), len(sub)
    lo, hi = _wilson(k, n)
    return {"rate": k / n if n else np.nan, "lo": lo, "hi": hi, "n": n}


def clutch_shift_by_season(shots: pd.DataFrame) -> pd.DataFrame:
    """Per-season clutch minus non-clutch 3PA rate."""
    rows = []
    for yr, g in shots.groupby("season"):
        c, r = g[g["is_clutch"]], g[~g["is_clutch"]]
        rows.append(
            {
                "season": int(yr),
                "nonclutch_3r": r["is_three"].mean(),
                "clutch_3r": c["is_three"].mean(),
                "shift_pp": (c["is_three"].mean() - r["is_three"].mean()) * 100,
                "clutch_n": len(c),
            }
        )
    return pd.DataFrame(rows).sort_values("season")


def rate_by_state(shots: pd.DataFrame) -> pd.DataFrame:
    """3PA rate by score state, clutch vs the Q1-Q3 baseline — the confound."""
    df = add_score_state(shots)
    rows = []
    for state in STATE_ORDER:
        clutch = df[(df["is_clutch"]) & (df["state"] == state)]
        base = df[(df["pressure"] == "Q1-Q3") & (df["state"] == state)]
        rows.append(
            {
                "state": state,
                "baseline_3r": base["is_three"].mean(),
                "baseline_n": len(base),
                "clutch_3r": clutch["is_three"].mean(),
                "clutch_n": len(clutch),
            }
        )
    return pd.DataFrame(rows)


def controlled_tests(shots: pd.DataFrame) -> pd.DataFrame:
    """Composure test with score state held constant.

    Compares clutch vs early (Q1-Q3) 3PA rate within matched closeness bands, so
    the trailing-team three-hunting confound cannot drive the result.
    """
    specs = [
        ("Tied", lambda d: d["margin_before"] == 0),
        ("Within 3", lambda d: d["abs_margin_before"] <= 3),
        ("Within 5", lambda d: d["abs_margin_before"] <= 5),
    ]
    rows = []
    for label, mask in specs:
        c = shots[shots["is_clutch"] & mask(shots)]
        r = shots[(~shots["is_clutch"]) & (shots["period"] <= 3) & mask(shots)]
        table = [
            [int(c["is_three"].sum()), int((~c["is_three"]).sum())],
            [int(r["is_three"].sum()), int((~r["is_three"]).sum())],
        ]
        _, p = stats.fisher_exact(table)
        rows.append(
            {
                "band": label,
                "early_3r": r["is_three"].mean(),
                "early_n": len(r),
                "clutch_3r": c["is_three"].mean(),
                "clutch_n": len(c),
                "shift_pp": (c["is_three"].mean() - r["is_three"].mean()) * 100,
                "fisher_p": p,
            }
        )
    return pd.DataFrame(rows)


def player_clutch_profiles(shots: pd.DataFrame, min_clutch: int = 60) -> pd.DataFrame:
    """Per-player clutch vs non-clutch 3PA rate (high-volume clutch shooters).

    Still confounded by which score states a given player takes clutch shots in,
    so this ranks *tendency*, not certified composure.
    """
    named = shots[shots["player"] != ""]
    rows = []
    for player, g in named.groupby("player"):
        c, r = g[g["is_clutch"]], g[~g["is_clutch"]]
        if len(c) < min_clutch or len(r) == 0:
            continue
        rows.append(
            {
                "player": player,
                "team": g["team"].mode().iloc[0],
                "nonclutch_3r": r["is_three"].mean(),
                "clutch_3r": c["is_three"].mean(),
                "shift_pp": (c["is_three"].mean() - r["is_three"].mean()) * 100,
                "clutch_n": len(c),
            }
        )
    return pd.DataFrame(rows).sort_values("shift_pp")
