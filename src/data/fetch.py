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
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def fetch_schedule_seasons(seasons: list[int]) -> dict[int, Path]:
    return {yr: fetch_schedule(yr) for yr in seasons}


def playoff_game_ids(seasons: list[int]) -> "list[tuple[int, str]]":
    """(season, game_id) for every completed playoff game in the given seasons.

    Playoffs are ``season_type == 3`` in the ESPN schedule.
    """
    import pandas as pd

    out: list[tuple[int, str]] = []
    for yr in seasons:
        sched = pd.read_parquet(fetch_schedule(yr))
        po = sched[(sched["season_type"] == 3) & (sched["status_type_completed"])]
        out.extend((yr, str(gid)) for gid in po["id"])
    return out


def _fetch_game_json_quiet(game_id: str) -> str | None:
    """Download one game JSON, returning the cache path or None on failure."""
    dest = RAW_DIR / "espn_games" / f"{game_id}.json"
    try:
        _download(f"{HOOPR_RAW}/nba/json/final/{game_id}.json", dest)
        return str(dest)
    except (urllib.error.URLError, OSError):
        return None


def fetch_games(game_ids: list[str], workers: int = 24, progress: bool = True) -> list[dict]:
    """Download many game JSONs concurrently (cached) and load them.

    Returns the list of successfully-loaded game dicts; missing/broken games
    are skipped rather than aborting the batch.
    """
    (RAW_DIR / "espn_games").mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_fetch_game_json_quiet, gid): gid for gid in game_ids}
        for fut in as_completed(futs):
            done += 1
            path = fut.result()
            if path:
                paths[futs[fut]] = path
            if progress and done % 100 == 0:
                print(f"  downloaded {done}/{len(game_ids)}")
    games = []
    for gid in game_ids:  # preserve input order
        p = paths.get(gid)
        if not p:
            continue
        try:
            with open(p) as fh:
                games.append(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    return games


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
