import pandas as pd
import numpy as np

def categorize_count(row):
    """Categorize pitch count into situation types"""
    balls = row['balls']
    strikes = row['strikes']
    
    if strikes == 2:
        return '2-strike (pressure)'
    elif balls >= 2 and strikes == 0:
        return 'Hitter ahead (2-0, 3-0)'
    elif balls == 3 and strikes == 2:
        return 'Full count situations'
    elif strikes >= balls:
        return 'Pitcher ahead'
    else:
        return 'Hitter ahead'

def calculate_zone_batting_average(df):
    # Copy the data to avoid modifying original
    df = df.copy()

    # Define which events count as hits
    hits = ["single", "double", "triple", "home_run"]
    
    # Define which events count as at-bats (excludes walks, HBP, sac flies, etc.)
    at_bat_events = [
        "single", "double", "triple", "home_run",
        "field_out", "force_out", "grounded_into_double_play",
        "strikeout", "strikeout_double_play", "fielders_choice_out",
        "double_play", "triple_play", "field_error", "fielders_choice"
    ]

    # Only keep rows with valid plate_x, plate_z, AND a valid at-bat event
    df = df.dropna(subset=["plate_x", "plate_z", "events"])
    df = df[df["events"].isin(at_bat_events)]  # Only actual at-bats

    # Assign zones using plate_x and plate_z
    df["zone_x"] = pd.cut(
        df["plate_x"], 
        bins=[-1.0, -0.33, 0.33, 1.0], 
        labels=["Left", "Middle", "Right"]
    )
    df["zone_z"] = pd.cut(
        df["plate_z"], 
        bins=[1.5, 2.3, 3.1, 3.9], 
        labels=["Low", "Mid", "High"]
    )

    # Compute hits and at-bats per zone
    grouped = (
        df.groupby(["zone_x", "zone_z"], observed=True)
        .apply(lambda x: pd.Series({
            "hits": (x["events"].isin(hits)).sum(),
            "abs": len(x)  # Now this is correct because we filtered to at-bat events only
        }), include_groups=False)
        .reset_index()
    )

    # Calculate batting average
    grouped["batting_avg"] = np.where(grouped["abs"] > 0, grouped["hits"] / grouped["abs"], np.nan)

    # Replace NaN batting averages with 0
    grouped["batting_avg"] = grouped["batting_avg"].fillna(0)

    # Rename for charting consistency
    grouped = grouped.rename(columns={"zone_x": "plate_x", "zone_z": "plate_z"})

    return grouped