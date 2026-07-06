import pandas as pd

from src.analysis.league import (
    add_score_state,
    controlled_tests,
    rate_by_state,
    score_state,
)
from src.data.parse import shot_value


def test_shot_value_from_text_when_points_missing():
    # old ESPN JSON leaves pointsAttempted null
    assert shot_value({"text": "makes  three point jumper"}) == 3
    assert shot_value({"text": "misses 18-foot two point jumper"}) == 2
    assert shot_value({"text": "makes layup"}) == 2
    assert shot_value({"text": "makes free throw 1 of 2"}) is None
    # explicit pointsAttempted wins
    assert shot_value({"pointsAttempted": 3, "text": "whatever"}) == 3


def test_score_state_buckets():
    assert score_state(-6) == "Trailing 4+"
    assert score_state(-2) == "Trailing 1-3"
    assert score_state(0) == "Tied"
    assert score_state(3) == "Leading 1-3"
    assert score_state(9) == "Leading 4+"


def _toy():
    # 4 shots: clutch tied 3, clutch tied 2, early tied 3, early tied 2
    return pd.DataFrame(
        {
            "is_three": [True, False, True, False],
            "is_clutch": [True, True, False, False],
            "period": [4, 4, 1, 1],
            "margin_before": [0, 0, 0, 0],
            "abs_margin_before": [0, 0, 0, 0],
            "pressure": pd.Categorical(
                ["Clutch", "Clutch", "Q1-Q3", "Q1-Q3"],
                ["Q1-Q3", "Q4 non-clutch", "Clutch"], ordered=True
            ),
        }
    )


def test_add_score_state():
    out = add_score_state(_toy())
    assert list(out["state"]) == ["Tied"] * 4


def test_rate_by_state_matches_counts():
    out = rate_by_state(_toy()).set_index("state")
    assert out.loc["Tied", "clutch_3r"] == 0.5
    assert out.loc["Tied", "baseline_3r"] == 0.5


def test_controlled_tests_runs():
    out = controlled_tests(_toy())
    assert set(out["band"]) == {"Tied", "Within 3", "Within 5"}
    tied = out[out["band"] == "Tied"].iloc[0]
    assert tied["clutch_3r"] == 0.5 and tied["early_3r"] == 0.5
