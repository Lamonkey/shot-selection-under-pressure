"""Matplotlib charts for the pressure study (light surface, palette-validated)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

# Reference palette (dataviz skill): categorical slots + chrome
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
TEAM_COLORS = {"NY": "#2a78d6", "SA": "#1baf7a"}  # slots 1-2, fixed order
# Ordinal blue ramp (steps 250/350/500/650) for the distance-ordered shot classes
CLASS_COLORS = {"rim": "#86b6ef", "short2": "#5598e7", "midrange": "#256abf", "three": "#104281"}
CLASS_LABELS = {"rim": "Rim", "short2": "Short 2 (5-13 ft)", "midrange": "Mid-range (14+ ft)", "three": "Three"}

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "font.family": "sans-serif",
        "text.color": INK,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "figure.dpi": 150,
    }
)


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def _title(fig, title: str, subtitle: str) -> None:
    fig.text(0.01, 0.985, title, fontsize=13, color=INK, fontweight="bold", va="top")
    fig.text(0.01, 0.925, subtitle, fontsize=9.5, color=MUTED, va="top")


def stakes_gradient(gradient: pd.DataFrame, path) -> None:
    """3PT attempt rate across the stakes gradient, one line per team.

    gradient: columns [stage, team, three_rate, fga]; stage is ordered.
    """
    stages = list(gradient["stage"].cat.categories)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    wide = gradient.pivot(index="stage", columns="team", values="three_rate").reindex(stages)
    for team in wide.columns:
        color = TEAM_COLORS[team]
        ax.plot(range(len(stages)), wide[team], color=color, linewidth=2,
                marker="o", markersize=8, markeredgecolor=SURFACE, markeredgewidth=2,
                label={"NY": "New York", "SA": "San Antonio"}[team])
        for i, rate in enumerate(wide[team]):
            # label above whichever team is higher at this stage, below the other
            above = rate == wide.iloc[i].max()
            ax.annotate(_pct(rate), (i, rate + (0.022 if above else -0.022)),
                        ha="center", va="bottom" if above else "top",
                        fontsize=9, color=color, fontweight="bold")
    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels([s.replace(" | ", "\n") for s in stages], fontsize=9, color=INK_2)
    ax.set_xlim(-0.3, len(stages) - 0.7)
    ax.set_ylim(0.15, 0.55)
    ax.set_yticks([0.2, 0.3, 0.4, 0.5])
    ax.set_yticklabels([_pct(v) for v in [0.2, 0.3, 0.4, 0.5]])
    ax.xaxis.grid(False)
    ax.legend(title=None, frameon=False, loc="lower left", labelcolor=INK_2)
    _title(fig, "Three-point attempt rate falls as the stakes rise",
           "Share of field-goal attempts from three  ·  2025-26 Spurs & Knicks  ·  Finals = 5 games")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def shot_mix_bars(mix: pd.DataFrame, path) -> None:
    """100% stacked horizontal bars of shot-class mix, one panel per team.

    mix: index (team, pressure), columns = shot classes, values = shares.
    """
    teams = mix.index.get_level_values(0).unique()
    fig, axes = plt.subplots(len(teams), 1, figsize=(9, 2.1 * len(teams) + 1.2), sharex=True)
    for ax, team in zip(axes, teams):
        sub = mix.loc[team].iloc[::-1]  # low stakes at bottom
        left = pd.Series(0.0, index=sub.index)
        for cls in mix.columns:
            vals = sub[cls]
            ax.barh(sub.index, vals, left=left, color=CLASS_COLORS[cls], height=0.62,
                    edgecolor=SURFACE, linewidth=2, label=CLASS_LABELS[cls])
            for y, (v, l) in enumerate(zip(vals, left)):
                if v >= 0.07:
                    ax.text(l + v / 2, y, _pct(v), ha="center", va="center", fontsize=8.5,
                            color="#ffffff" if cls in ("midrange", "three") else INK)
            left = left + vals
        ax.set_title({"NY": "New York Knicks", "SA": "San Antonio Spurs"}[team],
                     fontsize=11, color=INK, loc="left", fontweight="bold")
        ax.set_xlim(0, 1)
        ax.grid(False)
        ax.tick_params(axis="y", labelsize=9.5, labelcolor=INK_2)
        ax.set_xticks([])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, frameon=False, loc="lower center",
               bbox_to_anchor=(0.5, -0.01), fontsize=9, labelcolor=INK_2)
    fig.suptitle("Under pressure, threes give way to mid-range twos", x=0.01, ha="left",
                 fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


GOOD = "#0ca30c"     # status: shift toward more threes
CRITICAL = "#d03b3b"  # status: contraction (fewer threes)


def season_shift_bars(season_df: pd.DataFrame, path) -> None:
    """Per-season clutch-minus-nonclutch 3PA shift; diverging around zero."""
    df = season_df.sort_values("season")
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [CRITICAL if v < 0 else GOOD for v in df["shift_pp"]]
    bars = ax.bar(df["season"].astype(str), df["shift_pp"], color=colors,
                  width=0.66, edgecolor=SURFACE, linewidth=1)
    for b, v in zip(bars, df["shift_pp"]):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.15 if v >= 0 else -0.15),
                f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=8.5, color=INK_2)
    ax.axhline(0, color=BASELINE, linewidth=1)
    ax.set_ylim(-4, 7)
    ax.set_yticks([-4, -2, 0, 2, 4, 6])
    ax.set_yticklabels([f"{v:+d}pp" if v else "0" for v in [-4, -2, 0, 2, 4, 6]])
    ax.grid(axis="x", visible=False)
    ax.annotate("2026 Finals series\nlooked like this →", xy=(10, df.iloc[-1]["shift_pp"]),
                xytext=(7.2, -3.4), fontsize=8.5, color=INK_2,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1))
    _title(fig, "Do players really shoot fewer threes in the clutch? Usually not.",
           "Clutch minus non-clutch 3PT attempt rate, by playoff year  ·  green = more threes when it matters, red = fewer")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def state_confound_bars(state_df: pd.DataFrame, path) -> None:
    """3PA rate by score state: clutch vs baseline. Reveals the confound."""
    df = state_df.set_index("state").reindex(charts_state_order())
    x = range(len(df))
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    w = 0.38
    ax.bar([i - w / 2 for i in x], df["baseline_3r"], width=w, color=BASELINE,
           edgecolor=SURFACE, linewidth=1, label="Rest of game (Q1-Q3)")
    ax.bar([i + w / 2 for i in x], df["clutch_3r"], width=w, color=TEAM_COLORS["NY"],
           edgecolor=SURFACE, linewidth=1, label="Clutch (last 5:00, within 5)")
    for i, (_, r) in enumerate(df.iterrows()):
        ax.text(i - w / 2, r["baseline_3r"] + 0.006, _pct(r["baseline_3r"]), ha="center", fontsize=8, color=INK_2)
        ax.text(i + w / 2, r["clutch_3r"] + 0.006, _pct(r["clutch_3r"]), ha="center", fontsize=8, color=TEAM_COLORS["NY"], fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df.index, fontsize=9.5, color=INK_2)
    ax.set_ylim(0, 0.5)
    ax.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    ax.set_yticklabels([_pct(v) for v in [0, 0.1, 0.2, 0.3, 0.4, 0.5]])
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper right", fontsize=9, labelcolor=INK_2)
    ax.set_xlabel("Score state, shooter's team perspective", fontsize=9, color=MUTED)
    _title(fig, "It's the scoreboard, not the nerves: trailing teams hunt threes late",
           "Playoff 3PT attempt rate by score state  ·  2016-2026, 156k shots  ·  the clutch 'contraction' is really clock-milking by leaders")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def charts_state_order():
    return ["Trailing 4+", "Trailing 1-3", "Tied", "Leading 1-3", "Leading 4+"]


def player_dumbbell(players: pd.DataFrame, path) -> None:
    """Non-clutch vs clutch 3PT rate per player (Finals only).

    players: columns [player, team, nonclutch_3rate, clutch_3rate, clutch_fga].
    """
    df = players.sort_values("clutch_3rate", ascending=True).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(df) + 2.4))
    for i, row in df.iterrows():
        color = TEAM_COLORS[row["team"]]
        ax.plot([row["nonclutch_3rate"], row["clutch_3rate"]], [i, i], color=GRID, linewidth=2, zorder=1)
        ax.scatter(row["nonclutch_3rate"], i, s=64, color=BASELINE, zorder=2,
                   edgecolor=SURFACE, linewidth=1.5)
        ax.scatter(row["clutch_3rate"], i, s=90, color=color, zorder=3,
                   edgecolor=SURFACE, linewidth=1.5)
        ax.text(max(row["nonclutch_3rate"], row["clutch_3rate"]) + 0.02, i,
                f'{_pct(row["clutch_3rate"])} clutch ({int(row["clutch_fga"])} FGA)',
                va="center", fontsize=8.5, color=INK_2)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["player"], fontsize=10, color=INK)
    ax.yaxis.grid(False)
    ax.set_xlim(-0.01, 0.85)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8])
    ax.set_xticklabels([_pct(v) for v in [0, 0.2, 0.4, 0.6, 0.8]])
    ax.scatter([], [], s=64, color=BASELINE, label="Rest of game")
    ax.scatter([], [], s=90, color=INK_2, label="Clutch (colored by team)")
    ax.legend(frameon=False, loc="lower right", fontsize=9, labelcolor=INK_2)
    _title(fig, "Who keeps shooting threes when it matters?",
           "3PT share of FGA, 2026 Finals  ·  gray = non-clutch, colored = clutch (Q4/OT, last 5:00, within 5)")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
