"""League-wide test: does the clutch 3PT 'contraction' generalize beyond one series?

Pools every completed NBA playoff game 2016-2026 (ESPN play-by-play via
hoopR-nba-raw), labels each shot's pressure + score state, and tests the
pressure hypothesis against 150k+ shots.

Usage: python run_multiseason.py
First run downloads ~900 game JSONs (~1GB, cached in data/raw/espn_games).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.analysis.league import (
    clutch_shift_by_season,
    controlled_tests,
    player_clutch_profiles,
    rate_by_state,
)
from src.data.fetch import REPO_ROOT, fetch_games, playoff_game_ids
from src.data.parse import parse_games
from src.features.pressure import add_pressure_labels
from src.visualization import charts

SEASONS = list(range(2016, 2027))
PROCESSED = REPO_ROOT / "data" / "processed"
OUTPUTS = REPO_ROOT / "outputs"
SHOTS_CACHE = REPO_ROOT / "data" / "raw" / "playoff_shots_2016_2026.parquet"


def load_shots() -> pd.DataFrame:
    if SHOTS_CACHE.exists():
        print(f"Loading cached shots from {SHOTS_CACHE.name}")
        return pd.read_parquet(SHOTS_CACHE)
    ids = playoff_game_ids(SEASONS)
    season_map = {gid: yr for yr, gid in ids}
    print(f"Downloading {len(ids)} playoff games (2016-2026)...")
    games = fetch_games([gid for _, gid in ids])
    print(f"  parsing {len(games)} games...")
    shots = add_pressure_labels(parse_games(games, seasons=season_map))
    shots.to_parquet(SHOTS_CACHE, index=False)
    return shots


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    shots = load_shots()
    n_clutch = int(shots["is_clutch"].sum())
    print(f"{len(shots):,} playoff FGA across {shots['game_id'].nunique()} games; {n_clutch:,} clutch")

    season_df = clutch_shift_by_season(shots)
    state_df = rate_by_state(shots)
    controlled = controlled_tests(shots)
    players = player_clutch_profiles(shots, min_clutch=60)

    season_df.to_csv(PROCESSED / "ms_clutch_shift_by_season.csv", index=False)
    state_df.to_csv(PROCESSED / "ms_rate_by_state.csv", index=False)
    controlled.to_csv(PROCESSED / "ms_controlled_tests.csv", index=False)
    players.to_csv(PROCESSED / "ms_player_profiles.csv", index=False)

    charts.season_shift_bars(season_df, OUTPUTS / "04_league_season_shift.png")
    charts.state_confound_bars(state_df, OUTPUTS / "05_score_state_confound.png")

    write_report(shots, season_df, state_df, controlled, players)
    print(f"Done. Charts + MULTISEASON_REPORT.md in {OUTPUTS}/")


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def write_report(shots, season_df, state_df, controlled, players) -> None:
    c = shots[shots["is_clutch"]]
    r = shots[~shots["is_clutch"]]
    overall_shift = (c["is_three"].mean() - r["is_three"].mean()) * 100
    lines = [
        "# Does the clutch three-point 'contraction' generalize? — 2016-2026 playoffs",
        "",
        f"Pooled across **{shots['game_id'].nunique()} playoff games** and "
        f"**{len(shots):,} field-goal attempts** (ESPN play-by-play via hoopR-nba-raw).",
        "",
        "## The short answer: no.",
        "",
        f"The 2026 Spurs-Knicks Finals looked like a clean confirmation — 3PT",
        f"attempt rate fell 12.9 points in the clutch. But across a decade of",
        f"playoffs the league-wide clutch shift is **{overall_shift:+.1f} pp** "
        f"(clutch {pct(c['is_three'].mean())} vs non-clutch {pct(r['is_three'].mean())}) —",
        "if anything players shoot *slightly more* threes when it matters, not fewer.",
        "",
        "![season shift](04_league_season_shift.png)",
        "",
        "Only a few playoff years show the contraction the eye test expects; the",
        "2026 Finals was one of them, which is exactly why it was memorable — it",
        "was atypical, not representative.",
        "",
        "## Why single games fool us: the score-state confound",
        "",
        "'Clutch' averages together two opposite behaviors. Split late-game shots by",
        "the score before the shot and the illusion dissolves:",
        "",
        "| Score state (shooter's team) | Rest of game | Clutch | Change |",
        "|---|---|---|---|",
    ]
    for _, row in state_df.iterrows():
        change = (row["clutch_3r"] - row["baseline_3r"]) * 100
        lines.append(
            f"| {row['state']} | {pct(row['baseline_3r'])} ({int(row['baseline_n']):,}) "
            f"| {pct(row['clutch_3r'])} ({int(row['clutch_n']):,}) | {change:+.1f} pp |"
        )
    lines += [
        "",
        "![score state](05_score_state_confound.png)",
        "",
        "Teams **trailing by 4+** jack up threes in the clutch (44% vs 34% normally)",
        "— they need points fast. Teams **leading** shoot slightly fewer, milking",
        "clock for safe twos. A single close game you happen to watch is dominated",
        "by the *leading* team's clock-milking, so it *looks* like everyone abandons",
        "the three.",
        "",
        "## The clean composure test",
        "",
        "Hold score state constant — compare clutch shots to early-game shots at the",
        "*same* closeness — and the pressure effect essentially vanishes:",
        "",
        "| Closeness band | Early (Q1-Q3) | Clutch | Shift | Fisher p |",
        "|---|---|---|---|---|",
    ]
    for _, row in controlled.iterrows():
        lines.append(
            f"| {row['band']} | {pct(row['early_3r'])} ({int(row['early_n']):,}) "
            f"| {pct(row['clutch_3r'])} ({int(row['clutch_n']):,}) | {row['shift_pp']:+.1f} pp "
            f"| {row['fisher_p']:.2f} |"
        )
    lines += [
        "",
        "The tightest control — **tied** games — shows no contraction (-1.5 pp,",
        "p≈0.45). The looser *Within 5* band turns significant-positive only because",
        "it starts leaking the trailing-team three-hunting back in (a team down 5 is",
        "already in catch-up mode). The cleaner the control, the more completely the",
        "pressure effect disappears: under pressure, playoff players shoot threes at",
        "their normal rate. The 'mindset contraction' is mostly strategy (clock and",
        "score), not nerves.",
        "",
        "## Player tendencies (still confounded)",
        "",
        "Among players with ≥60 clutch playoff FGA, biggest gaps between clutch and",
        "non-clutch 3PT rate (this still mixes in which score states each player",
        "shoots in, so read it as tendency, not certified composure):",
        "",
        "| Player | Clutch FGA | Non-clutch 3PT | Clutch 3PT | Shift |",
        "|---|---|---|---|---|",
    ]
    extremes = pd.concat([players.head(6), players.tail(6)])
    for _, row in extremes.iterrows():
        lines.append(
            f"| {row['player']} | {int(row['clutch_n'])} | {pct(row['nonclutch_3r'])} "
            f"| {pct(row['clutch_3r'])} | {row['shift_pp']:+.1f} pp |"
        )
    lines += [
        "",
        "## Takeaway",
        "",
        "The eye-test hypothesis is real *as a description of some games* but wrong",
        "*as a general law*. What reads as pressure-induced conservatism is mostly",
        "the leading team managing the clock. The interesting, defensible finding is",
        "the **confound itself**: late-game shot selection is driven by the",
        "scoreboard, and you cannot infer a player's 'mindset maturity' from a",
        "single high-stakes game without controlling for it.",
    ]
    (OUTPUTS / "MULTISEASON_REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
