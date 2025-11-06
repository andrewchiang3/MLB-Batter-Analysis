import pandas as pd
import pybaseball as pyb
import unicodedata
import streamlit as st

def normalize_text(text):
    """Remove accents from text for easier searching"""
    if pd.isna(text) or text is None:
        return ""
    # Normalize unicode characters and remove accent marks
    nfd = unicodedata.normalize('NFD', str(text))
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

@st.cache_data(ttl=3600)
def get_statcast_players():
    """Get list of all players who have Statcast data (2015-present)"""
    lookup = pyb.chadwick_register()
    
    # Filter for players who played in MLB during Statcast era (2015+)
    statcast_players = lookup[
        (lookup['mlb_played_last'].notna()) & 
        (lookup['mlb_played_last'] >= 2015)
    ].copy()
    
    # Create full name with accent marks preserved
    statcast_players['full_name'] = (
        statcast_players['name_first'].fillna('') + ' ' + 
        statcast_players['name_last'].fillna('')
    ).str.strip()
    
    # Create normalized version for searching (without accents)
    statcast_players['normalized_name'] = statcast_players['full_name'].apply(normalize_text)
    
    # Add years for disambiguation
    statcast_players['display_name'] = statcast_players.apply(
        lambda row: f"{row['full_name']} ({int(row['mlb_played_first'])}-{int(row['mlb_played_last'])})",
        axis=1
    )
    
    # Sort by most recent first
    statcast_players = statcast_players.sort_values(
        ['mlb_played_last', 'full_name'], 
        ascending=[False, True]
    )
    
    return statcast_players[['full_name', 'display_name', 'normalized_name']]

def search_players(searchterm: str):
    """Search function for streamlit-searchbox - returns list of matching players"""
    if not searchterm:
        return []
    
    # Get cached player list
    players_df = get_statcast_players()
    
    # Normalize search term
    normalized_search = normalize_text(searchterm).lower()
    
    # Filter players whose normalized name contains the search term
    matches = players_df[
        players_df['normalized_name'].str.lower().str.contains(normalized_search, na=False)
    ].head(20)  # Limit to top 20 results
    
    # Return list of display names
    return matches['display_name'].tolist()

def get_player_full_name(display_name: str):
    """Convert display name to full name"""
    if not display_name:
        return None
    
    players_df = get_statcast_players()
    matching = players_df[players_df['display_name'] == display_name]
    
    if not matching.empty:
        return matching['full_name'].iloc[0]
    return None