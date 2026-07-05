# Shot Selection Under Pressure 🏀🧠

> How does high-stakes pressure affect NBA shot selection?

## Hypothesis

In high-stakes NBA games (playoffs, clutch moments, close games), players tend to deviate from their normal shot selection patterns:

- **Low stakes** (blowout games, early quarters, wide score gaps): Players shoot more 3-pointers, playing their natural game
- **High stakes** (4th quarter, last 5 minutes, score tied or within 3 points): Players **contract** — fewer 3s, more mid-range jumpers and layups

This shift in shot selection serves as a **proxy for mindset maturity** — the ability to maintain composure and stick to one's game under pressure.

## Research Questions

1. Do players shoot significantly fewer 3-pointers in clutch vs non-clutch situations?
2. Which players/teams show the greatest shot selection shift under pressure?
3. Does experience (veteran vs young players) correlate with smaller shot selection changes?
4. Are there differences between regular season, playoffs, and Finals?

## Methodology

### Data Sources
- NBA.com stats API (via `nba_api` Python package)
- Play-by-play data with shot coordinates, shot type, game clock, score differential

### Key Metrics
- **3PT Rate**: % of total field goal attempts that are 3-pointers
- **Shot Zone Distribution**: Restricted area, paint, mid-range, corner 3, above-the-break 3
- **Clutch Definition**: Last 5 minutes of 4th quarter/OT, score within 5 points
- **Pressure Index**: Combined metric of game importance + score closeness + time remaining

### Visualization
- Shot chart heatmaps (high stakes vs low stakes)
- 3PT rate decay curves as stakes increase
- Individual player pressure profiles

## Project Structure

```
shot-selection-under-pressure/
├── data/               # Raw and processed data
│   ├── raw/           # Raw NBA API data
│   └── processed/     # Cleaned, feature-engineered data
├── notebooks/          # Jupyter notebooks for analysis
├── src/               # Reusable source code
│   ├── data/          # Data collection and processing
│   ├── features/      # Feature engineering (pressure index, etc.)
│   ├── analysis/      # Statistical analysis
│   └── visualization/ # Plotting and charting
├── outputs/           # Generated charts, tables, reports
├── requirements.txt   # Dependencies
└── README.md          # This file
```

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## License

MIT