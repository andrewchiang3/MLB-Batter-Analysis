# MLB Batter Analysis

A comprehensive Streamlit application for analyzing MLB batter performance using Statcast data (2015-present). Built for casual fans and analysts who want to dive deep into player statistics with visualizations.

![MLB Batter Analysis](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.0%2B-red)

## Features

### Player Search & Bio
- **Smart Player Search**: Autocomplete search with player names and career years
- **Player Information**: Headshot, team logo, position, batting/throwing hand, physical stats
- **Comprehensive Stats**: Traditional batting statistics (AVG, OBP, SLG, OPS, HR, RBI, etc.)

### Advanced Visualizations

#### Rolling xwOBA Tracker
- Interactive rolling expected weighted on-base average (xwOBA) chart
- Tracks performance over plate appearances with smooth trend lines
- Hover to see xwOBA value and date of last plate appearance
- Compare against MLB league average

#### Spray Chart
- Visual representation of where hits landed on the field
- Color-coded by hit type (single, double, triple, home run)
- Understand a batter's tendencies and patterns

#### Strike Zone Heatmaps
- Batting average by zone (3x3 grid)
- Color-coded performance (red = hot zones, blue = cold zones)
- See exactly where batters perform best

#### Plate Discipline Analysis
- **Chase Rate**: How often batters swing at pitches outside the zone
- **Zone Swing Rate**: Swing percentage on pitches in the zone
- **Situational Chase Rates**: By count situation (hitter ahead, pitcher ahead, 2-strike pressure)
- Compare against MLB averages

### Situational Splits

#### Clutch Performance
- 2 Outs with RISP (Runners in Scoring Position)
- Late & Close situations (7th inning+, within 1 run)
- Performance by score margin (ahead, behind, tie game, within 1-4 runs)

#### Count Analysis
- Performance heatmap by ball-strike count (0-0 through 3-2)
- Individual count situations (0-2, 3-2, etc.)
- Aggregate counts (batter ahead, pitcher ahead, full count)

#### Platoon Splits
- Interactive radar chart comparing vs LHP and vs RHP
- Visualize AVG, OBP, SLG, and OPS differences
- Identify platoon advantages/disadvantages

#### Ballpark Performance
- Statistics at every stadium visited
- Identify which parks favor the batter
- Beautiful card display of best-performing ballpark

### Pitcher vs Batter Matchups
- Select any pitcher the batter has faced
- View pitch sequences for every at-bat
- Strike zone visualizations for each pitch
- Outcome distribution pie charts
- Summary statistics for the matchup

## Getting Started

### Prerequisites

```bash
Python 3.10 or higher
pip (Python package manager)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/mlb-batter-analysis.git
cd mlb-batter-analysis
```

2. **Install required packages**
```bash
pip install -r requirements.txt
```

Required packages:
- `streamlit` - Web application framework
- `pybaseball` - MLB data retrieval
- `pandas` - Data manipulation
- `altair` - Interactive visualizations
- `streamlit-searchbox` - Enhanced search functionality

3. **Run the application**
```bash
streamlit run mlb_app.py
```

The app will open in your default web browser at `http://localhost:8501`

## How to Use

### 1. Search for a Player
- Start typing a player's name in the search box
- Select from the autocomplete dropdown (includes career years for disambiguation)
- **Example**: "Aaron Judge (2016-2024)"

### 2. Select Date Range
- Choose start and end dates for analysis
- Statcast data available from **April 2015 to present**
- **Tip**: Season-long analysis or specific month comparisons work great

### 3. Load Data
- Click "Load Player Data" button
- The app will retrieve and process all pitch-by-pitch data
- Loading time varies based on date range (typically 5-15 seconds)

### 4. Explore the Visualizations
- Scroll through different sections
- Hover over charts for detailed tooltips
- Use the pitcher matchup dropdown to analyze specific head-to-head performance

### 5. Change Players or Dates
- Use the quick search bar at the top to switch players
- Adjust date ranges without losing your place
- Click "Load Data" to refresh

## Project Structure

```
mlb-batter-analysis/
│
├── mlb_app.py                  # Main application file
├── data_loader.py              # Data retrieval functions
├── player_search.py            # Player search with autocomplete
├── player_bio.py               # Player info and images
├── visualizations.py           # Main visualization functions
├── splits.py                   # Situational splits calculator
├── splits_visualizations.py    # Splits-specific charts
├── matchup.py                  # Pitcher vs batter analysis
├── utils.py                    # Helper functions
└── README.md                   # This file
```

## Key Technologies

- **Streamlit**: Fast, interactive web app framework
- **PyBaseball**: Official Statcast data from MLB
- **Altair**: Declarative statistical visualizations
- **Pandas**: Data manipulation and analysis

## Data Source

All data comes from **MLB's Statcast system** via the `pybaseball` library:
- Pitch-by-pitch tracking data
- Exit velocity, launch angle, spin rate
- Player biographical information
- Official MLB statistics

**Note**: Data is cached locally to improve performance and reduce API calls.

## Known Limitations

1. **Runs (R) in Splits**: Individual runs scored are not available in pitch-by-pitch Statcast data. The 'R' column in splits will show 0. Use season totals for accurate run information.

2. **RBI Calculation**: RBI calculations are conservative and based on score differentials. They may not match official totals in edge cases.

3. **Data Availability**: Statcast era begins in 2015. No data available before this date.

4. **Cache Updates**: Player data is cached. Recent games may require clearing cache to appear.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **MLB & Statcast** for providing comprehensive baseball data
- **PyBaseball** maintainers for the excellent Python wrapper
- **Streamlit** team for the web framework
- The baseball analytics community for inspiration

*Last Updated: November 2025*