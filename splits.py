"""
Baseball Splits Calculator for Pybaseball Statcast Data
========================================================

Simple function-based API for calculating batting splits in Streamlit apps.
All functions accept a pybaseball statcast DataFrame and return a formatted DataFrame.

IMPORTANT NOTE ON RUNS (R):
----------------------------
Runs scored by the batter are NOT available in pitch-by-pitch statcast data.
The 'R' column will always show 0 in the output. To get accurate run totals:
1. Use pybaseball.batting_stats() for season totals
2. Use game logs with pybaseball.schedule_and_record() for game-level runs
3. The RBI calculations ARE accurate using score differentials

Usage in Streamlit:
-------------------
from pybaseball import statcast_batter
import baseball_splits as splits

# Get data from pybaseball
df = statcast_batter('2024-04-01', '2024-09-30', 660271)  # Juan Soto

# Get splits - each returns a DataFrame
clutch_df = splits.get_clutch_splits(df)
count_df = splits.get_count_splits(df)
ballpark_df = splits.get_ballpark_splits(df)
platoon_df = splits.get_platoon_splits(df)
home_away_df = splits.get_home_away_splits(df)
inning_df = splits.get_inning_splits(df)
first_pitch_df = splits.get_first_pitch_splits(df)

# Display in Streamlit
import streamlit as st
st.dataframe(clutch_df)
"""

import pandas as pd
import numpy as np


# ============================================================================
# CORE STATS CALCULATION
# ============================================================================

def calculate_stats(df):
    """
    Calculate batting statistics for a DataFrame of pitches.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame (filtered to a specific split)
        
    Returns:
    --------
    dict : Dictionary with all batting statistics
    """
    # Get unique plate appearances
    pa_list = df.groupby(['game_pk', 'at_bat_number']).size()
    pa = len(pa_list)
    
    # Filter to pitch outcomes (events that end the PA)
    events = df[df['events'].notna()].copy()
    
    if len(events) == 0:
        return _empty_stats()
    
    # Count outcomes
    hits = events['events'].isin(['single', 'double', 'triple', 'home_run']).sum()
    singles = (events['events'] == 'single').sum()
    doubles = (events['events'] == 'double').sum()
    triples = (events['events'] == 'triple').sum()
    hr = (events['events'] == 'home_run').sum()
    bb = events['events'].isin(['walk']).sum()
    ibb = events['events'].isin(['intent_walk']).sum()
    hbp = events['events'].isin(['hit_by_pitch']).sum()
    so = events['events'].isin(['strikeout', 'strikeout_double_play']).sum()
    sac_hit = events['events'].isin(['sac_bunt', 'sac_bunt_double_play']).sum()
    sac_fly = events['events'].isin(['sac_fly', 'sac_fly_double_play']).sum()
    gdp = events['events'].str.contains('double_play', na=False).sum() - \
          events['events'].isin(['sac_bunt_double_play', 'sac_fly_double_play']).sum()
    
    # Calculate AB
    ab = pa - bb - hbp - sac_hit - sac_fly
    
    # Runs - NOT directly available in pitch-by-pitch data
    # Runs scored by the batter are not tracked in statcast pitch data
    # Setting to 0 as it cannot be accurately calculated from pitch data alone
    runs = 0
    
    # RBI - Calculate from score differential with conservative event type filtering
    # Only count events that reliably produce RBI according to official scoring
    rbi = 0
    if 'post_bat_score' in events.columns and 'bat_score' in events.columns:
        for idx, event_row in events.iterrows():
            event_type = event_row['events']
            
            # Conservative list - events that reliably get RBI credit
            # Removed: field_error, fielders_choice, force_out, double_play
            # These don't always result in RBI being awarded by official scorer
            rbi_eligible_events = [
                'single', 'double', 'triple', 'home_run',
                'sac_fly', 'sac_fly_double_play',
                'field_out',  # Keep this but be cautious
                'grounded_into_double_play'  # Can have RBI
            ]
            
            # Check if this event type can produce RBI
            if event_type in rbi_eligible_events:
                if pd.notna(event_row['post_bat_score']) and pd.notna(event_row['bat_score']):
                    score_change = event_row['post_bat_score'] - event_row['bat_score']
                    if score_change > 0:
                        rbi += int(score_change)
            
            # Special case: Walk or HBP with bases loaded
            elif event_type in ['walk', 'intent_walk', 'hit_by_pitch']:
                # Check if bases were loaded (all three bases occupied)
                if (pd.notna(event_row.get('on_1b')) and 
                    pd.notna(event_row.get('on_2b')) and 
                    pd.notna(event_row.get('on_3b'))):
                    if pd.notna(event_row['post_bat_score']) and pd.notna(event_row['bat_score']):
                        score_change = event_row['post_bat_score'] - event_row['bat_score']
                        if score_change > 0:
                            rbi += int(score_change)
    
    elif 'delta_run_exp' in events.columns:
        # Fallback - less accurate but better than nothing
        # Still filter by event type
        rbi_eligible = events[events['events'].isin([
            'single', 'double', 'triple', 'home_run',
            'sac_fly', 'sac_fly_double_play',
            'field_out', 'grounded_into_double_play'
        ])]
        positive_changes = rbi_eligible['delta_run_exp'].fillna(0)
        rbi = int(positive_changes[positive_changes > 0].sum())
    
    # Rate stats
    ba = hits / ab if ab > 0 else 0
    obp = (hits + bb + hbp) / (ab + bb + hbp + sac_fly) if (ab + bb + hbp + sac_fly) > 0 else 0
    tb = singles + (2 * doubles) + (3 * triples) + (4 * hr)
    slg = tb / ab if ab > 0 else 0
    ops = obp + slg
    
    # BABIP
    balls_in_play = ab - so - hr
    hits_in_play = hits - hr
    babip = hits_in_play / balls_in_play if balls_in_play > 0 else 0
    
    # Games - count unique games where player had at least one completed PA
    # Note: game_pk should uniquely identify each game including doubleheaders
    if len(events) > 0:
        # Count unique game_pk values
        games = events['game_pk'].nunique()
        
        # Fallback: if game_pk has issues, try game_date + teams combo
        # This shouldn't normally be needed but provides robustness
        if 'game_date' in events.columns and games == 0:
            games = events['game_date'].nunique()
    else:
        games = 0
    
    return {
        'G': games,
        'PA': pa,
        'AB': int(ab),
        'R': runs,
        'H': int(hits),
        '2B': int(doubles),
        '3B': int(triples),
        'HR': int(hr),
        'RBI': rbi,
        'BB': int(bb),
        'SO': int(so),
        'BA': round(ba, 3),
        'OBP': round(obp, 3),
        'SLG': round(slg, 3),
        'OPS': round(ops, 3),
        'TB': int(tb),
        'GDP': int(gdp),
        'HBP': int(hbp),
        'SH': int(sac_hit),
        'SF': int(sac_fly),
        'IBB': int(ibb),
        'BAbip': round(babip, 3)
    }


def _empty_stats():
    """Return empty stats dictionary."""
    return {
        'G': 0, 'PA': 0, 'AB': 0, 'R': 0, 'H': 0, '2B': 0, '3B': 0,
        'HR': 0, 'RBI': 0, 'BB': 0, 'SO': 0, 'BA': 0.0, 'OBP': 0.0,
        'SLG': 0.0, 'OPS': 0.0, 'TB': 0, 'GDP': 0, 'HBP': 0, 'SH': 0,
        'SF': 0, 'IBB': 0, 'BAbip': 0.0
    }


# ============================================================================
# SPLIT FUNCTIONS - Each returns a DataFrame ready for Streamlit
# ============================================================================

def get_clutch_splits(df):
    """
    Calculate clutch situation splits.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Clutch splits with columns: Split, G, PA, AB, R, H, 2B, 3B, HR, etc.
    """
    results = []
    
    # 2 outs, RISP
    mask = (df['outs_when_up'] == 2) & ((df['on_2b'].notna()) | (df['on_3b'].notna()))
    if mask.sum() > 0:
        stats = calculate_stats(df[mask])
        stats['Split'] = '2 Outs, RISP'
        results.append(stats)
    
    # Late & Close (7th inning or later, score within 1 run)
    if 'bat_score_diff' in df.columns:
        mask = (df['inning'] >= 7) & (df['bat_score_diff'].abs() <= 1)
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = 'Late & Close'
            results.append(stats)
    
    # Tie Game
    if 'bat_score_diff' in df.columns:
        mask = df['bat_score_diff'] == 0
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = 'Tie Game'
            results.append(stats)
    
    # Within N runs
    if 'bat_score_diff' in df.columns:
        for n in [1, 2, 3, 4]:
            mask = df['bat_score_diff'].abs() <= n
            if mask.sum() > 0:
                stats = calculate_stats(df[mask])
                stats['Split'] = f'Within {n}R'
                results.append(stats)
        
        # Margin > 4 runs
        mask = df['bat_score_diff'].abs() > 4
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = 'Margin >4R'
            results.append(stats)
        
        # Ahead
        mask = df['bat_score_diff'] > 0
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = 'Ahead'
            results.append(stats)
        
        # Behind
        mask = df['bat_score_diff'] < 0
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = 'Behind'
            results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    # Reorder columns to put Split first
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_count_splits(df):
    """
    Calculate splits by ball-strike count.
    
    IMPORTANT: For count splits, we only count plate appearances that END at each count.
    For example, "0-0 Count" means PAs where the final pitch was thrown at 0-0.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Count splits
    """
    results = []
    
    # Filter to only events (outcomes that end PAs)
    events_df = df[df['events'].notna()].copy()
    
    if len(events_df) == 0:
        return pd.DataFrame()
    
    # Individual counts (0-0 through 3-2)
    # These are PAs where the FINAL pitch was at this count
    for balls in range(4):
        for strikes in range(3):
            mask = (events_df['balls'] == balls) & (events_df['strikes'] == strikes)
            if mask.sum() > 0:
                stats = calculate_stats(events_df[mask])
                stats['Split'] = f'{balls}-{strikes} Count'
                results.append(stats)
    
    # Full count (3-2) - already included above but add separate label
    mask = (events_df['balls'] == 3) & (events_df['strikes'] == 2)
    if mask.sum() > 0:
        stats = calculate_stats(events_df[mask])
        stats['Split'] = 'Full Count'
        results.append(stats)
    
    # "After" counts - these mean the count REACHED this point at some time during the PA
    # We need to look at ALL pitches, not just final outcomes
    after_counts = [
        ('After 1-0', (df['balls'] >= 1) & (df['strikes'] == 0)),
        ('After 2-0', (df['balls'] >= 2) & (df['strikes'] == 0)),
        ('After 3-0', (df['balls'] >= 3) & (df['strikes'] == 0)),
        ('After 0-1', (df['balls'] == 0) & (df['strikes'] >= 1)),
        ('After 1-1', (df['balls'] >= 1) & (df['strikes'] >= 1)),
        ('After 2-1', (df['balls'] >= 2) & (df['strikes'] >= 1)),
        ('After 3-1', (df['balls'] >= 3) & (df['strikes'] >= 1)),
        ('After 0-2', (df['balls'] == 0) & (df['strikes'] >= 2)),
        ('After 1-2', (df['balls'] >= 1) & (df['strikes'] >= 2)),
        ('After 2-2', (df['balls'] >= 2) & (df['strikes'] >= 2)),
    ]
    
    for name, mask in after_counts:
        # Get unique PAs that had this count at some point
        pas_with_count = df[mask].groupby(['game_pk', 'at_bat_number']).size()
        
        if len(pas_with_count) > 0:
            # Get the events for these specific PAs
            pa_keys = pas_with_count.index.tolist()
            events_mask = events_df.apply(
                lambda row: (row['game_pk'], row['at_bat_number']) in pa_keys, 
                axis=1
            )
            
            if events_mask.sum() > 0:
                stats = calculate_stats(events_df[events_mask])
                stats['Split'] = name
                results.append(stats)
    
    # Aggregate counts - these also check if count was REACHED during PA
    aggregates = [
        ('Zero Balls', (df['balls'] == 0)),
        ('Zero Strikes', (df['strikes'] == 0)),
        ('Three Balls', (df['balls'] == 3)),
        ('Two Strikes', (df['strikes'] == 2)),
        ('Batter Ahead', (df['balls'] > df['strikes'])),
        ('Even Count', (df['balls'] == df['strikes'])),
        ('Pitcher Ahead', (df['strikes'] > df['balls'])),
    ]
    
    for name, mask in aggregates:
        # Get unique PAs that had this count at some point
        pas_with_count = df[mask].groupby(['game_pk', 'at_bat_number']).size()
        
        if len(pas_with_count) > 0:
            # Get the events for these specific PAs
            pa_keys = pas_with_count.index.tolist()
            events_mask = events_df.apply(
                lambda row: (row['game_pk'], row['at_bat_number']) in pa_keys,
                axis=1
            )
            
            if events_mask.sum() > 0:
                stats = calculate_stats(events_df[events_mask])
                stats['Split'] = name
                results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_first_pitch_splits(df):
    """
    Calculate splits based on first pitch action (swung vs took).
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : First pitch splits
    """
    results = []
    
    # Get first pitch of each PA
    first_pitch = df[df['pitch_number'] == 1].copy()
    
    if len(first_pitch) == 0:
        return pd.DataFrame()
    
    # Find PAs where first pitch was swung at
    # Include: swinging_strike, foul, foul_tip, hit_into_play, swinging_strike_blocked
    swung_descriptions = [
        'swinging_strike', 'foul', 'foul_tip', 'hit_into_play', 
        'swinging_strike_blocked', 'foul_bunt', 'missed_bunt',
        'bunt_foul_tip', 'foul_pitchout'
    ]
    
    swung_abs = first_pitch[
        first_pitch['description'].isin(swung_descriptions)
    ][['game_pk', 'at_bat_number']].drop_duplicates()
    
    # Find PAs where first pitch was taken
    # Include: ball, called_strike, blocked_ball, pitchout, hit_by_pitch
    took_descriptions = [
        'ball', 'called_strike', 'blocked_ball', 'pitchout', 
        'hit_by_pitch', 'intent_ball'
    ]
    
    took_abs = first_pitch[
        first_pitch['description'].isin(took_descriptions)
    ][['game_pk', 'at_bat_number']].drop_duplicates()
    
    # Get all pitches for those PAs
    if len(swung_abs) > 0:
        swung_df = df.merge(swung_abs, on=['game_pk', 'at_bat_number'], how='inner')
        stats = calculate_stats(swung_df)
        stats['Split'] = 'Swung 1st Pitch'
        results.append(stats)
    
    if len(took_abs) > 0:
        took_df = df.merge(took_abs, on=['game_pk', 'at_bat_number'], how='inner')
        stats = calculate_stats(took_df)
        stats['Split'] = 'Took 1st Pitch'
        results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_ballpark_splits(df):
    """
    Calculate splits by ballpark (home_team).
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Ballpark splits
    """
    results = []
    
    if 'home_team' not in df.columns:
        return pd.DataFrame()
    
    ballparks = df['home_team'].dropna().unique()
    
    for park in sorted(ballparks):
        mask = df['home_team'] == park
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = park
            results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_inning_splits(df):
    """
    Calculate splits by inning.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Inning splits
    """
    results = []
    
    if 'inning' not in df.columns:
        return pd.DataFrame()
    
    innings = sorted(df['inning'].dropna().unique())
    
    for inning in innings:
        mask = df['inning'] == inning
        if mask.sum() > 0:
            stats = calculate_stats(df[mask])
            stats['Split'] = f'Inning {int(inning)}'
            results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_platoon_splits(df):
    """
    Calculate splits vs LHP and RHP.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Platoon splits
    """
    results = []
    
    if 'p_throws' not in df.columns:
        return pd.DataFrame()
    
    # vs LHP
    mask = df['p_throws'] == 'L'
    if mask.sum() > 0:
        stats = calculate_stats(df[mask])
        stats['Split'] = 'vs LHP'
        results.append(stats)
    
    # vs RHP
    mask = df['p_throws'] == 'R'
    if mask.sum() > 0:
        stats = calculate_stats(df[mask])
        stats['Split'] = 'vs RHP'
        results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_home_away_splits(df):
    """
    Calculate home vs away splits.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Home/Away splits
    """
    results = []
    
    if 'inning_topbot' not in df.columns:
        return pd.DataFrame()
    
    # Home (batting in bottom of inning)
    mask = df['inning_topbot'] == 'Bot'
    if mask.sum() > 0:
        stats = calculate_stats(df[mask])
        stats['Split'] = 'Home'
        results.append(stats)
    
    # Away (batting in top of inning)
    mask = df['inning_topbot'] == 'Top'
    if mask.sum() > 0:
        stats = calculate_stats(df[mask])
        stats['Split'] = 'Away'
        results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_month_splits(df):
    """
    Calculate splits by month.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    pd.DataFrame : Monthly splits
    """
    results = []
    
    if 'game_date' not in df.columns:
        return pd.DataFrame()
    
    # Convert game_date to datetime if needed
    df_copy = df.copy()
    df_copy['game_date'] = pd.to_datetime(df_copy['game_date'])
    df_copy['month'] = df_copy['game_date'].dt.month
    
    months = sorted(df_copy['month'].dropna().unique())
    month_names = {3: 'March', 4: 'April', 5: 'May', 6: 'June', 
                   7: 'July', 8: 'August', 9: 'September', 10: 'October'}
    
    for month in months:
        mask = df_copy['month'] == month
        if mask.sum() > 0:
            stats = calculate_stats(df_copy[mask])
            stats['Split'] = month_names.get(month, f'Month {month}')
            results.append(stats)
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    cols = ['Split'] + [col for col in result_df.columns if col != 'Split']
    return result_df[cols]


def get_all_splits(df):
    """
    Get all available splits in a dictionary.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Pybaseball statcast DataFrame
        
    Returns:
    --------
    dict : Dictionary with split names as keys and DataFrames as values
           Example: {'clutch': DataFrame, 'count': DataFrame, ...}
    """
    splits = {
        'clutch': get_clutch_splits(df),
        'count': get_count_splits(df),
        'first_pitch': get_first_pitch_splits(df),
        'ballpark': get_ballpark_splits(df),
        'inning': get_inning_splits(df),
        'platoon': get_platoon_splits(df),
        'home_away': get_home_away_splits(df),
        'month': get_month_splits(df),
    }
    
    # Return only non-empty DataFrames
    return {k: v for k, v in splits.items() if not v.empty}


# ============================================================================
# STREAMLIT HELPER FUNCTIONS
# ============================================================================

def format_percentage_columns(df):
    """
    Format BA, OBP, SLG, OPS, BAbip as percentages for display.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Splits DataFrame
        
    Returns:
    --------
    pd.DataFrame : Formatted DataFrame
    """
    if df.empty:
        return df
    
    display_df = df.copy()
    pct_cols = ['BA', 'OBP', 'SLG', 'OPS', 'BAbip']
    
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}")
    
    return display_df


def get_summary_stats(df):
    """
    Get summary statistics from a splits DataFrame.
    Useful for Streamlit metric cards.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Splits DataFrame
        
    Returns:
    --------
    dict : Summary stats (PA, AB, H, HR, BA, OBP, SLG, OPS)
    """
    if df.empty or 'PA' not in df.columns:
        return {}
    
    # Sum counting stats, weighted average for rate stats
    total_pa = df['PA'].sum()
    total_ab = df['AB'].sum()
    total_h = df['H'].sum()
    total_hr = df['HR'].sum()
    
    ba = total_h / total_ab if total_ab > 0 else 0
    
    # For OBP, SLG, OPS - calculate from totals
    total_bb = df['BB'].sum()
    total_hbp = df['HBP'].sum()
    total_sf = df['SF'].sum()
    total_tb = df['TB'].sum()
    
    obp = (total_h + total_bb + total_hbp) / (total_ab + total_bb + total_hbp + total_sf) if (total_ab + total_bb + total_hbp + total_sf) > 0 else 0
    slg = total_tb / total_ab if total_ab > 0 else 0
    ops = obp + slg
    
    return {
        'PA': int(total_pa),
        'AB': int(total_ab),
        'H': int(total_h),
        'HR': int(total_hr),
        'BA': round(ba, 3),
        'OBP': round(obp, 3),
        'SLG': round(slg, 3),
        'OPS': round(ops, 3),
    }
