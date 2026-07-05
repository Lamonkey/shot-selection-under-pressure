"""End-to-end analysis: 2026 Finals shot selection under pressure.

Usage: python run_analysis.py
Downloads (and caches) all inputs into data/raw, writes processed tables to
data/processed and charts + report to outputs/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.analysis.shot_mix import (
    baseline_three_rate,
    clutch_shift_test,
    norm_name,
    shot_class_mix,
    three_rate,
)
from src.data.fetch import REPO_ROOT, fetch_finals_games, fetch_shotdetail_csv
from src.data.parse import parse_finals_shots
from src.features.pressure import add_pressure_labels
from src.visualization import charts

TEAMS = {"San Antonio Spurs": "SA", "New York Knicks": "NY"}
STAGES = ["Regular season", "Playoffs | R1-R2", "Finals | Q1-Q3", "Finals | Q4 non-clutch", "Finals | clutch"]
MIN_CLUTCH_FGA = 6

PROCESSED = REPO_ROOT / "data" / "processed"
OUTPUTS = REPO_ROOT / "outputs"


def stage_rates_from_shotdetail(csv_path, stage: str) -> pd.DataFrame:
    sd = pd.read_csv(csv_path, usecols=["TEAM_NAME", "SHOT_TYPE"])
    sd = sd[sd["TEAM_NAME"].isin(TEAMS)]
    sd["team"] = sd["TEAM_NAME"].map(TEAMS)
    sd["is_three"] = sd["SHOT_TYPE"].str.startswith("3PT")
    g = sd.groupby("team")["is_three"].agg(fga="count", threes="sum").reset_index()
    g["three_rate"] = g["threes"] / g["fga"]
    g["stage"] = stage
    return g


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    print("Fetching 2026 Finals play-by-play (ESPN via hoopR-nba-raw)...")
    shots = add_pressure_labels(parse_finals_shots(fetch_finals_games()))
    shots.to_csv(PROCESSED / "finals_2026_shots.csv", index=False)
    print(f"  {len(shots)} field-goal attempts, {int(shots['is_clutch'].sum())} in the clutch")

    print("Fetching baselines (stats.nba.com via shufinskiy/nba_data)...")
    rs_csv = fetch_shotdetail_csv("shotdetail_2025")      # 2025-26 regular season
    po_csv = fetch_shotdetail_csv("shotdetail_po_2025")   # 2025-26 playoffs through 5/9 (pre-Finals)

    # --- stakes gradient (team level) ---
    finals_rates = three_rate(shots, ["team", "pressure"])
    finals_rates["stage"] = finals_rates["pressure"].map(
        {"Q1-Q3": "Finals | Q1-Q3", "Q4 non-clutch": "Finals | Q4 non-clutch", "Clutch": "Finals | clutch"}
    )
    gradient = pd.concat(
        [
            stage_rates_from_shotdetail(rs_csv, "Regular season"),
            stage_rates_from_shotdetail(po_csv, "Playoffs | R1-R2"),
            finals_rates[["team", "fga", "threes", "three_rate", "stage"]],
        ],
        ignore_index=True,
    )
    gradient["stage"] = pd.Categorical(gradient["stage"], STAGES, ordered=True)
    gradient = gradient.sort_values(["team", "stage"])
    gradient.to_csv(PROCESSED / "stakes_gradient.csv", index=False)

    # --- shot-class mix by pressure ---
    mix = shot_class_mix(shots, ["team", "pressure"])
    mix.to_csv(PROCESSED / "shot_class_mix.csv")

    # --- team + combined significance tests ---
    team_tests = clutch_shift_test(shots, "team")
    combined = clutch_shift_test(shots.assign(all="Both teams"), "all")
    tests = pd.concat([team_tests.rename(columns={"team": "group"}), combined.rename(columns={"all": "group"})])
    tests.to_csv(PROCESSED / "clutch_shift_tests.csv", index=False)

    # --- per player: clutch vs rest, with regular-season baseline ---
    players = clutch_shift_test(shots[shots["player"] != ""], "player")
    players = players[players["clutch_fga"] >= MIN_CLUTCH_FGA]
    team_of = shots.groupby("player")["team"].agg(lambda s: s.mode()[0])
    players["team"] = players["player"].map(team_of)
    rs_base = baseline_three_rate(rs_csv, list(TEAMS))
    players["player_key"] = players["player"].map(norm_name)
    players = players.merge(
        rs_base[["player_key", "three_rate"]].rename(columns={"three_rate": "rs_three_rate"}),
        on="player_key", how="left",
    ).drop(columns="player_key")
    players.to_csv(PROCESSED / "player_clutch_shift.csv", index=False)

    # --- charts ---
    charts.stakes_gradient(gradient, OUTPUTS / "01_stakes_gradient.png")
    charts.shot_mix_bars(mix, OUTPUTS / "02_shot_mix_by_pressure.png")
    charts.player_dumbbell(players, OUTPUTS / "03_player_clutch_shift.png")

    write_report(shots, gradient, mix, tests, players)
    print(f"Done. Charts + report in {OUTPUTS}/, tables in {PROCESSED}/")


def fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def write_report(shots, gradient, mix, tests, players) -> None:
    lines = [
        "# Shot Selection Under Pressure — 2026 NBA Finals (Spurs vs Knicks)",
        "",
        "**Hypothesis.** In high-stakes moments players abandon the three-point shot",
        "they take freely in low-stakes minutes, contracting toward mid-range jumpers",
        "and drives — a behavioral tell of pressure.",
        "",
        "**Data.** All 862 field-goal attempts of the five 2026 Finals games",
        "(ESPN play-by-play via `sportsdataverse/hoopR-nba-raw`), plus 2025-26",
        "regular-season and pre-Finals playoff shot charts (stats.nba.com via",
        "`shufinskiy/nba_data`) as baselines. *Clutch* = 4th quarter or OT, last",
        "5:00, score within 5 points before the shot (NBA.com definition).",
        "",
        "## 1. The stakes gradient",
        "",
        "Three-point attempt rate (share of FGA) by stage:",
        "",
        "| Stage | " + " | ".join(sorted(shots["team"].unique())) + " |",
        "|---|---|---|",
    ]
    for stage in gradient["stage"].cat.categories:
        row = [stage.replace(" | ", " — ")]
        for team in sorted(shots["team"].unique()):
            sub = gradient[(gradient["stage"] == stage) & (gradient["team"] == team)]
            row.append(f"{fmt_pct(sub['three_rate'].iloc[0])} ({int(sub['fga'].iloc[0])} FGA)" if len(sub) else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "",
        "![stakes gradient](01_stakes_gradient.png)",
        "",
        "## 2. Clutch vs the rest of the Finals",
        "",
        "| Group | Non-clutch 3PT rate | Clutch 3PT rate | Shift | Fisher p |",
        "|---|---|---|---|---|",
    ]
    for _, r in tests.iterrows():
        lines.append(
            f"| {r['group']} | {fmt_pct(r['nonclutch_3rate'])} ({int(r['nonclutch_fga'])}) "
            f"| {fmt_pct(r['clutch_3rate'])} ({int(r['clutch_fga'])}) "
            f"| {r['diff'] * 100:+.1f} pp | {r['fisher_p']:.3f} |"
        )
    lines += [
        "",
        "![shot mix](02_shot_mix_by_pressure.png)",
        "",
        "## 3. Player-level shifts",
        "",
        f"Players with ≥{MIN_CLUTCH_FGA} clutch FGA in the series:",
        "",
        "| Player | Team | RS 3PT rate | Finals non-clutch | Finals clutch | Shift |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in players.sort_values("diff").iterrows():
        rs = fmt_pct(r["rs_three_rate"]) if pd.notna(r["rs_three_rate"]) else "—"
        lines.append(
            f"| {r['player']} | {r['team']} | {rs} | {fmt_pct(r['nonclutch_3rate'])} ({int(r['nonclutch_fga'])}) "
            f"| {fmt_pct(r['clutch_3rate'])} ({int(r['clutch_fga'])}) | {r['diff'] * 100:+.1f} pp |"
        )
    lines += [
        "",
        "![player shifts](03_player_clutch_shift.png)",
        "",
        "## Caveats",
        "",
        "- **Five games.** 68 clutch FGA total; only the pooled shift approaches",
        "  conventional significance. This is a case study, not a league-wide result.",
        "- **Defense is not held constant.** Clutch possessions face set half-court",
        "  defenses that take away the arc; part of the shift is imposed, not chosen.",
        "- **Lineups change late.** Coaches play their closers; the clutch shot mix",
        "  partly reflects *who* shoots, not just *how* they choose.",
        "- **Intentional strategy.** Trailing teams hunt quick 2s + fouls; leading",
        "  teams milk clock into isolations. Both depress 3PT rate for reasons that",
        "  are rational rather than psychological.",
        "",
        "Next step: run the same pipeline over many playoff series (and regular-season",
        "clutch minutes) so player-level 'pressure profiles' have real sample sizes.",
    ]
    (OUTPUTS / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
