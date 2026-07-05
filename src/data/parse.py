"""Parse ESPN game JSON into a per-shot dataframe."""

from __future__ import annotations

import re

import pandas as pd

DIST_RE = re.compile(r"(\d+)-foot")
RIM_TYPES = ("layup", "dunk", "tip")


def _player_map(game: dict) -> dict[str, str]:
    """athlete id -> display name, from the boxscore block."""
    out: dict[str, str] = {}
    for team in game.get("boxscore", {}).get("players", []):
        for stat_block in team.get("statistics", []):
            for ath in stat_block.get("athletes", []):
                a = ath.get("athlete", {})
                if a.get("id"):
                    out[str(a["id"])] = a.get("displayName", "")
    return out


def _shot_distance(play: dict) -> float | None:
    """Distance in feet, parsed from the play text (e.g. '26-foot three point
    jumper'). Layups/dunks/tips usually omit it -> treat as at-rim (1 ft)."""
    m = DIST_RE.search(play.get("text") or "")
    if m:
        return float(m.group(1))
    type_text = (play.get("type.text") or "").lower()
    if any(t in type_text for t in RIM_TYPES):
        return 1.0
    return None


def classify_shot(is_three: bool, type_text: str, distance: float | None) -> str:
    """Bucket a field-goal attempt: three / rim / short2 / midrange.

    rim      = layups, dunks, tips, or any 2PT within 4 ft
    short2   = floaters/hooks/short jumpers 5-13 ft (paint, non-rim)
    midrange = 2PT jumpers from 14 ft out
    """
    if is_three:
        return "three"
    tt = (type_text or "").lower()
    if any(t in tt for t in RIM_TYPES):
        return "rim"
    if distance is None:
        return "short2"  # rare: non-rim 2PT with no listed distance
    if distance <= 4:
        return "rim"
    if distance < 14:
        return "short2"
    return "midrange"


def parse_game_shots(game: dict) -> pd.DataFrame:
    """All field-goal attempts of one game with pre-shot score context."""
    players = _player_map(game)
    plays = game["plays"]
    home_id = str(plays[0]["homeTeamId"])
    rows = []
    for p in plays:
        if not p.get("shootingPlay"):
            continue
        pts = p.get("pointsAttempted")
        if pts not in (2, 3):  # skip free throws
            continue
        made = bool(p.get("scoringPlay"))
        team_is_home = str(p.get("team.id")) == home_id
        # ESPN scores are post-play; back out the shooter's points if it went in
        home_after, away_after = p["homeScore"], p["awayScore"]
        score_value = p.get("scoreValue", 0) if made else 0
        home_before = home_after - (score_value if team_is_home else 0)
        away_before = away_after - (score_value if not team_is_home else 0)
        margin_before = (home_before - away_before) if team_is_home else (away_before - home_before)

        # "11:45" above one minute, "58.3" (seconds.tenths) below it
        clock = p.get("clock.displayValue") or "0:00"
        if ":" in clock:
            mm, _, ss = clock.partition(":")
            clock_seconds = int(mm) * 60 + float(ss or 0)
        else:
            clock_seconds = float(clock)

        distance = _shot_distance(p)
        is_three = pts == 3
        rows.append(
            {
                "game_id": str(p["game_id"]),
                "period": p["period.number"],
                "clock_seconds": clock_seconds,
                "team": p["homeTeamAbbrev"] if team_is_home else p["awayTeamAbbrev"],
                "player": players.get(str(p.get("participants.0.athlete.id")), ""),
                "is_three": is_three,
                "made": made,
                "distance_ft": distance,
                "shot_class": classify_shot(is_three, p.get("type.text", ""), distance),
                "margin_before": margin_before,  # shooter's team perspective
                "abs_margin_before": abs(margin_before),
                "type_text": p.get("type.text", ""),
            }
        )
    return pd.DataFrame(rows)


def parse_finals_shots(games: list[dict]) -> pd.DataFrame:
    df = pd.concat([parse_game_shots(g) for g in games], ignore_index=True)
    order = {gid: i + 1 for i, gid in enumerate(sorted(df["game_id"].unique()))}
    df["game_num"] = df["game_id"].map(order)
    return df
