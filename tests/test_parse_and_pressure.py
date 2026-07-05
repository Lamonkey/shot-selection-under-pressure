import pandas as pd

from src.data.parse import classify_shot, parse_game_shots
from src.features.pressure import add_pressure_labels


def test_classify_shot():
    assert classify_shot(True, "Jump Shot", 26) == "three"
    assert classify_shot(False, "Driving Layup Shot", None) == "rim"
    assert classify_shot(False, "Pullup Jump Shot", 3) == "rim"
    assert classify_shot(False, "Floating Jump Shot", 9) == "short2"
    assert classify_shot(False, "Pullup Jump Shot", 18) == "midrange"
    assert classify_shot(False, "Jump Shot", None) == "short2"


def _play(**over):
    base = {
        "shootingPlay": True,
        "pointsAttempted": 3,
        "scoringPlay": True,
        "scoreValue": 3,
        "team.id": "18",
        "homeScore": 0,
        "awayScore": 3,
        "period.number": 1,
        "clock.displayValue": "11:45",
        "type.text": "Jump Shot",
        "text": "Player A makes 26-foot three point jumper",
        "participants.0.athlete.id": "1",
        "game_id": 401859963,
        "homeTeamId": 24,
        "homeTeamAbbrev": "SA",
        "awayTeamAbbrev": "NY",
    }
    base.update(over)
    return base


def _game(plays):
    return {"plays": plays, "boxscore": {}}


def test_margin_is_pre_shot():
    # away player hits a three: score after is 0-3, margin before must be 0
    shots = parse_game_shots(_game([_play()]))
    assert shots.loc[0, "margin_before"] == 0
    # home player misses with home up 90-88: margin stays +2 from shooter's view
    shots = parse_game_shots(_game([_play(
        **{"team.id": "24", "scoringPlay": False, "scoreValue": 0,
           "pointsAttempted": 2, "homeScore": 90, "awayScore": 88}
    )]))
    assert shots.loc[0, "margin_before"] == 2


def test_free_throws_excluded():
    ft = _play(pointsAttempted=1, **{"type.text": "Free Throw - 1 of 2"})
    assert len(parse_game_shots(_game([ft]))) == 0


def test_sub_minute_clock():
    shots = parse_game_shots(_game([_play(**{"clock.displayValue": "58.3"})]))
    assert shots.loc[0, "clock_seconds"] == 58.3


def test_clutch_label():
    df = pd.DataFrame(
        {
            "period": [4, 4, 4, 2],
            "clock_seconds": [200, 200, 400, 100],
            "abs_margin_before": [3, 9, 3, 1],
        }
    )
    out = add_pressure_labels(df)
    assert list(out["is_clutch"]) == [True, False, False, False]
    assert list(out["pressure"]) == ["Clutch", "Q4 non-clutch", "Q4 non-clutch", "Q1-Q3"]
