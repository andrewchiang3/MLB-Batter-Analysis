import pybaseball as pyb
import pandas as pd

# Enable cache
pyb.cache.enable()

def load_statcast_data(start_date, end_date):
    """Load Statcast data for the given date range with player names"""
    # Load the data
    data = pyb.statcast(
        start_dt=start_date.strftime('%Y-%m-%d'), 
        end_dt=end_date.strftime('%Y-%m-%d'),
    )
    
    # Get player lookup table
    lookup = pyb.chadwick_register()
    
    # Merge with names
    data = data.merge(
        lookup[['key_mlbam', 'name_first', 'name_last']], 
        left_on='batter', 
        right_on='key_mlbam', 
        how='left'
    )
    data['batter_name'] = data['name_first'] + ' ' + data['name_last']
    
    return data

def load_batting_stats(start_date, end_date, name):
    """Load baseball reference stats from a user defined time range using MLB ID"""
    # Split the name into first and last
    name_parts = name.split(' ', 1)
    if len(name_parts) == 2:
        first_name, last_name = name_parts
    else:
        # Handle single name edge case
        first_name = name_parts[0]
        last_name = ''
    
    # Look up the player to get their MLB ID
    try:
        player_info = pyb.playerid_lookup(last_name, first_name)
        
        if player_info.empty:
            return pd.DataFrame()
        
        # Get the MLB ID (key_mlbam) - this is what batting_stats_range uses
        mlb_id = player_info['key_mlbam'].iloc[0]
        
        if pd.isna(mlb_id):
            return pd.DataFrame()
        
        # Load batting stats for the date range
        data = pyb.batting_stats_range(
            start_dt=start_date.strftime('%Y-%m-%d'), 
            end_dt=end_date.strftime('%Y-%m-%d')
        )
        
        # Filter by MLB ID (the 'mlbID' column in batting_stats_range)
        player_data = data[data['mlbID'] == int(mlb_id)]
        
        return player_data
        
    except Exception as e:
        print(f"Error looking up player: {e}")
        return pd.DataFrame()
