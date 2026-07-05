"""Shot-mix aggregation and significance tests."""

from __future__ import annotations

import pandas as pd
from scipy import stats

SHOT_CLASS_ORDER = ["rim", "short2", "midrange", "three"]


def norm_name(name: str) -> str:
    """Join key across ESPN and stats.nba.com spellings (O.G. vs OG, etc.)."""
    return name.replace(".", "").strip().lower()


def three_rate(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, observed=True)["is_three"].agg(fga="count", threes="sum").reset_index()
    g["three_rate"] = g["threes"] / g["fga"]
    return g


def shot_class_mix(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    counts = (
        df.groupby(by + ["shot_class"], observed=True)
        .size()
        .unstack("shot_class", fill_value=0)
        .reindex(columns=SHOT_CLASS_ORDER, fill_value=0)
    )
    return counts.div(counts.sum(axis=1), axis=0)


def baseline_three_rate(shotdetail_csv, team_names: list[str]) -> pd.DataFrame:
    """Per-player 3PT attempt rate from a stats.nba.com shot-detail CSV."""
    sd = pd.read_csv(
        shotdetail_csv,
        usecols=["PLAYER_NAME", "TEAM_NAME", "SHOT_TYPE", "SHOT_ATTEMPTED_FLAG"],
    )
    sd = sd[sd["TEAM_NAME"].isin(team_names)]
    sd["is_three"] = sd["SHOT_TYPE"].str.startswith("3PT")
    out = (
        sd.groupby(["TEAM_NAME", "PLAYER_NAME"])["is_three"]
        .agg(fga="count", threes="sum")
        .reset_index()
        .rename(columns={"TEAM_NAME": "team_name", "PLAYER_NAME": "player"})
    )
    out["three_rate"] = out["threes"] / out["fga"]
    out["player_key"] = out["player"].map(norm_name)
    return out


def clutch_shift_test(shots: pd.DataFrame, by: str = "team") -> pd.DataFrame:
    """Fisher exact test: is the 3PT share different in clutch vs non-clutch?

    Small clutch samples (a 5-game series) make Fisher's exact test the
    right tool over a z-test.
    """
    rows = []
    for key, grp in shots.groupby(by, observed=True):
        clutch = grp[grp["is_clutch"]]
        rest = grp[~grp["is_clutch"]]
        if len(clutch) == 0 or len(rest) == 0:
            continue
        table = [
            [int(clutch["is_three"].sum()), int((~clutch["is_three"]).sum())],
            [int(rest["is_three"].sum()), int((~rest["is_three"]).sum())],
        ]
        odds, p = stats.fisher_exact(table)
        rows.append(
            {
                by: key,
                "clutch_fga": len(clutch),
                "clutch_3rate": clutch["is_three"].mean(),
                "nonclutch_fga": len(rest),
                "nonclutch_3rate": rest["is_three"].mean(),
                "diff": clutch["is_three"].mean() - rest["is_three"].mean(),
                "fisher_p": p,
            }
        )
    return pd.DataFrame(rows).sort_values("diff")
