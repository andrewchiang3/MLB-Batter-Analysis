from PIL import Image
import requests
from io import BytesIO
import pandas as pd
import streamlit as st

# Function to get an image from a URL and display it on the given axis
def player_headshot(player_id: str):
    # Construct the URL for the player's headshot image
    url = f'https://img.mlbstatic.com/mlb-photos/image/'\
          f'upload/d_people:generic:headshot:67:current.png'\
          f'/w_640,q_auto:best/v1/people/{player_id}/headshot/silo/current.png'

    # Send a GET request to the URL
    response = requests.get(url)

    # Open the image from the response content
    img = Image.open(BytesIO(response.content))

    return img

def player_bio(player_id: str):
    # Construct the URL to fetch player data
    url = f"https://statsapi.mlb.com/api/v1/people?personIds={player_id}&hydrate=currentTeam"

    # Send a GET request to the URL and parse the JSON response
    data = requests.get(url).json()

    player = data['people'][0]

    # Extract player information from the JSON data
    bio = {
        'name': player['fullName'],
        'age': player['currentAge'],
        'height': player['height'],
        'weight': player['weight'],
        'bats': player['batSide']['description'],  # "Right" or "Left"
        'throws': player['pitchHand']['description'],  # "Right" or "Left"
        'position': player['primaryPosition']['abbreviation'],
        'team': player.get('currentTeam', {}).get('name', 'N/A'),
        'number': player.get('primaryNumber', 'N/A')
    }
    
    return bio
    
# Team logo
# List of MLB teams and their corresponding ESPN logo URLs
mlb_teams = [
    {"team": "AZ", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/ari.png&h=500&w=500"},
    {"team": "ATL", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/atl.png&h=500&w=500"},
    {"team": "BAL", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/bal.png&h=500&w=500"},
    {"team": "BOS", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/bos.png&h=500&w=500"},
    {"team": "CHC", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/chc.png&h=500&w=500"},
    {"team": "CWS", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/chw.png&h=500&w=500"},
    {"team": "CIN", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/cin.png&h=500&w=500"},
    {"team": "CLE", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/cle.png&h=500&w=500"},
    {"team": "COL", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/col.png&h=500&w=500"},
    {"team": "DET", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/det.png&h=500&w=500"},
    {"team": "HOU", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/hou.png&h=500&w=500"},
    {"team": "KC", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/kc.png&h=500&w=500"},
    {"team": "LAA", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/laa.png&h=500&w=500"},
    {"team": "LAD", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/lad.png&h=500&w=500"},
    {"team": "MIA", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/mia.png&h=500&w=500"},
    {"team": "MIL", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/mil.png&h=500&w=500"},
    {"team": "MIN", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/min.png&h=500&w=500"},
    {"team": "NYM", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/nym.png&h=500&w=500"},
    {"team": "NYY", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/nyy.png&h=500&w=500"},
    {"team": "OAK", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/oak.png&h=500&w=500"},
    {"team": "PHI", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/phi.png&h=500&w=500"},
    {"team": "PIT", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/pit.png&h=500&w=500"},
    {"team": "SD", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/sd.png&h=500&w=500"},
    {"team": "SF", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/sf.png&h=500&w=500"},
    {"team": "SEA", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/sea.png&h=500&w=500"},
    {"team": "STL", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/stl.png&h=500&w=500"},
    {"team": "TB", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/tb.png&h=500&w=500"},
    {"team": "TEX", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/tex.png&h=500&w=500"},
    {"team": "TOR", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/tor.png&h=500&w=500"},
    {"team": "WSH", "logo_url": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/mlb/500/scoreboard/wsh.png&h=500&w=500"}
]

# Create a DataFrame from the list of dictionaries
df_image = pd.DataFrame(mlb_teams)
image_dict = df_image.set_index('team')['logo_url'].to_dict()

def team_logo(player_id: str):
    # Construct the URL to fetch player data
    url = f"https://statsapi.mlb.com/api/v1/people?personIds={player_id}&hydrate=currentTeam"

    # Send a GET request to the URL and parse the JSON response
    data = requests.get(url).json()

    # Construct the URL to fetch team data
    url_team = 'https://statsapi.mlb.com/' + data['people'][0]['currentTeam']['link']

    # Send a GET request to the team URL and parse the JSON response
    data_team = requests.get(url_team).json()

    # Extract the team abbreviation
    team_abb = data_team['teams'][0]['abbreviation']

    # Get the logo URL from the image dictionary using the team abbreviation
    logo_url = image_dict[team_abb]

    # Send a GET request to the logo URL
    response = requests.get(logo_url)

    # Open the image from the response content
    img = Image.open(BytesIO(response.content))

    return img


# Player stats
def load_stats(batting_data):
    # Games and PA
    with st.container(horizontal = True, gap = "medium"):
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "Games",
                batting_data['G'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "PA",
                batting_data['PA'],
                width="content"
            )

        # AB and R
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "AB",
                batting_data['AB'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "R",
                batting_data['R'],
                width="content"
            )

        # H and 2B
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "Hits",
                batting_data['H'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "2B",
                batting_data['2B'],
                width="content"
            )

        # H and 2B
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "3B",
                batting_data['3B'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "HR",
                batting_data['HR'],
                width="content"
            )

        # RBI and BB
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "RBIs",
                batting_data['RBI'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "BB + IBB",
                batting_data['BB'] + batting_data['IBB'],
                width="content"
            )

        # HBP and SO
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "HBP",
                batting_data['HBP'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "SO",
                batting_data['SO'],
                width="content"
            )

        # SB and CS
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "SB",
                batting_data['SB'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "CS",
                batting_data['CS'],
                width="content"
            )

        # Avg and obp
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "AVG",
                batting_data['BA'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "OBP",
                batting_data['OBP'],
                width="content"
            )

        # H and 2B
        cols = st.columns(2, gap='medium', width=300)

        with cols[0]:
            st.metric(
                "SLG",
                batting_data['SLG'],
                width="content"
            )
        
        with cols[1]:
            st.metric(
                "OPS",
                batting_data['OPS'],
                width="content"
            )