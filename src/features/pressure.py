"""Pressure/stakes labelling for shot attempts."""

from __future__ import annotations

import pandas as pd

CLUTCH_SECONDS = 300  # last 5:00
CLUTCH_MARGIN = 5     # score within 5 (NBA.com clutch definition)

# Ordered from lowest to highest stakes; used consistently in charts/tables.
PRESSURE_ORDER = ["Q1-Q3", "Q4 non-clutch", "Clutch"]


def add_pressure_labels(shots: pd.DataFrame) -> pd.DataFrame:
    """Label each Finals shot with a within-game pressure bucket.

    Clutch = 4th quarter or OT, last 5 minutes, score within 5 points
    (margin measured BEFORE the shot).
    """
    df = shots.copy()
    late = (df["period"] >= 4) & (df["clock_seconds"] <= CLUTCH_SECONDS)
    df["is_clutch"] = late & (df["abs_margin_before"] <= CLUTCH_MARGIN)
    df["pressure"] = "Q1-Q3"
    df.loc[df["period"] >= 4, "pressure"] = "Q4 non-clutch"
    df.loc[df["is_clutch"], "pressure"] = "Clutch"
    df["pressure"] = pd.Categorical(df["pressure"], PRESSURE_ORDER, ordered=True)
    return df
