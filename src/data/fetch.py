"""Data fetching for the 2026 NBA Finals shot-selection study.

Two GitHub-hosted mirrors are used so the pipeline works without access to
stats.nba.com / espn.com (both are frequently blocked from cloud runners):

1. sportsdataverse/hoopR-nba-raw — raw ESPN play-by-play JSON per game,
   updated nightly. Used for the Finals games (running score, clock, shot
   descriptions, coordinates).
2. shufinskiy/nba_data — stats.nba.com shot-chart detail archived per season
   (tar.xz in the repo tree). Used for regular-season and early-playoff
   baselines (official shot zones).
"""

from __future__ import annotations

import json
import tarfile
import urllib.request
from pathlib import Path

HOOPR_RAW = "https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-raw/main"
NBA_DATA_RAW = "https://raw.githubusercontent.com/shufinskiy/nba_data/main/datasets"

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"

# 2026 NBA Finals: San Antonio Spurs vs New York Knicks (NY won 4-1)
FINALS_2026_GAME_IDS = [
    "401859963",  # Game 1, 2026-06-03  NY 105 @ SA 95
    "401859964",  # Game 2, 2026-06-05  NY 105 @ SA 104
    "401859965",  # Game 3, 2026-06-08  SA 115 @ NY 111
    "401859966",  # Game 4, 2026-06-10  SA 106 @ NY 107
    "401859967",  # Game 5, 2026-06-13  NY 94  @ SA 90
]


def _download(url: str, dest: Path, timeout: int = 300) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "shot-selection-study"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    return dest


def fetch_schedule(season: int = 2026) -> Path:
    """Season schedule parquet (ESPN, via hoopR). Season is the end year."""
    return _download(
        f"{HOOPR_RAW}/nba/schedules/parquet/nba_schedule_{season}.parquet",
        RAW_DIR / f"nba_schedule_{season}.parquet",
    )


def fetch_game_json(game_id: str) -> dict:
    """Raw ESPN game JSON (plays + boxscore) for one game."""
    path = _download(
        f"{HOOPR_RAW}/nba/json/final/{game_id}.json",
        RAW_DIR / "espn_games" / f"{game_id}.json",
    )
    with open(path) as fh:
        return json.load(fh)


def fetch_finals_games() -> list[dict]:
    return [fetch_game_json(gid) for gid in FINALS_2026_GAME_IDS]


def fetch_shotdetail_csv(name: str) -> Path:
    """Download + extract a shufinskiy/nba_data shot-detail archive.

    name examples: 'shotdetail_2025' (2025-26 regular season),
    'shotdetail_po_2025' (2025-26 playoffs, through 2026-05-09).
    """
    csv_path = RAW_DIR / f"{name}.csv"
    if csv_path.exists():
        return csv_path
    archive = _download(f"{NBA_DATA_RAW}/{name}.tar.xz", RAW_DIR / f"{name}.tar.xz")
    with tarfile.open(archive) as tar:
        tar.extract(f"{name}.csv", RAW_DIR)
    return csv_path
