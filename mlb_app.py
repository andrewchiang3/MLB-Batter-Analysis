import streamlit as st
import pandas as pd
from streamlit_searchbox import st_searchbox


# Modules
from player_search import search_players, get_player_full_name
from data_loader import load_statcast_data, load_batting_stats
from player_bio import player_headshot, player_bio, team_logo, load_stats
from visualizations import *
from utils import calculate_zone_batting_average
from matchup import pitcher_matchup
from splits import *
from splits_visualizations import *

# App configuration
st.set_page_config(
    page_title = "MLB",
    layout = 'wide'
)

# Main page layout
st.title("MLB Batter Analysis")
st.write("Performance metrics for MLB players")

# Check if data is loaded
if 'data' not in st.session_state:
    # Main page when no data is loaded
    st.markdown("---")
    st.subheader("Get Started")
    st.write("Enter a player name and select a date range to begin analysis")

    # Columns for layout
    col1, col2, col3 = st.columns([2, 1, 1])

    # Player search box
    with col1:
        # Use searchbox for autocomplete
        selected_player_display = st_searchbox(
            search_players,
            label = "Batter Name",
            placeholder = "Start typing a player name...",
            clear_on_submit = False,
            key = "player_searchbox"
        )

        # Get actual name from display name
        player_name = get_player_full_name(selected_player_display)

        if selected_player_display and not player_name:
            st.warning("Please select a valid player from the dropdown")

    # Date input
    with col2:
        start_date = st.date_input(
            "**Start Date**",
            value=pd.to_datetime('2025-03-27'),
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            help="Statcast era: 2015-present"
        )

    with col3:
        end_date = st.date_input(
            "**End Date:**",
            value=pd.to_datetime('2025-04-07'),
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            help="Select the end date for analysis"
        )

    # Validation
    validation_errors = []
    if not player_name:
        validation_errors.append("Please select a player")
    if start_date > end_date:
        validation_errors.append("Start date must be before end date")
    
    if validation_errors:
        for error in validation_errors:
            st.error(f"{error}")
        load_button_disabled = True
    else:
        load_button_disabled = False
    
    st.markdown("")

    # Load button
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        if st.button(
            "Load Player Data", 
            type="primary", 
            disabled=load_button_disabled,
            use_container_width=True
        ):
            with st.spinner(f"Loading data for {player_name} from {start_date} to {end_date}..."):
                try:
                    batting_data = load_batting_stats(start_date, end_date, str(player_name))
                    player_id = batting_data['mlbID'].iloc[0]
                    bio = player_bio(player_id)
                    data = load_statcast_data(start_date, end_date)
                    
                    st.session_state['batting_data'] = batting_data
                    st.session_state['data'] = data
                    st.session_state['bio'] = bio
                    st.session_state['player_name'] = player_name
                    st.session_state['start_date'] = start_date
                    st.session_state['end_date'] = end_date
                    
                    st.success(f"Successfully loaded {len(data):,} pitches!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error loading data: {e}")

# Data is already loaded, switch if user wants to
else:
    st.markdown("---")

    # Quick search bar at the top
    col_search, col_button = st.columns([4, 1])

    with col_search:
        new_selected_display = st_searchbox(
            search_players,
            label="Search Different Player:",
            placeholder="Type player name to switch...",
            clear_on_submit=False,
            key="quick_player_search"
        )

        new_player_name = get_player_full_name(new_selected_display) if new_selected_display else None

    with col_button:
        st.markdown("")  # Spacing to align with searchbox
        st.markdown("")  # More spacing
        if st.button("Load Player", type="primary", disabled=not new_player_name, use_container_width=True):
            # Update session state with new player name
            st.session_state['player_name'] = new_player_name
            
            # Load new data immediately
            with st.spinner(f"Loading data for {new_player_name}..."):
                try:
                    new_batting_data = load_batting_stats(
                        st.session_state['start_date'], 
                        st.session_state['end_date'],
                        st.session_state['player_name']
                    )

                    new_player_id = new_batting_data['mlbID'].iloc[0]

                    new_data = load_statcast_data(
                        st.session_state['start_date'], 
                        st.session_state['end_date'],
                    )

                    bio = player_bio(new_player_id)
                    
                    # Update with new data
                    st.session_state['bio'] = bio
                    st.session_state['data'] = new_data
                    st.session_state['batting_data'] = new_batting_data
                    st.success(f"Loaded {len(new_data):,} pitches for {new_player_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading data: {e}")

    # Analysis
    player_data = st.session_state['data'][
        st.session_state['data']['batter_name'] == st.session_state['player_name']
    ]

    batting_data = st.session_state['batting_data']
    
    if len(player_data) == 0:
        st.error(f"No data found for **{st.session_state['player_name']}**")
        st.write("**Possible reasons:**")
        st.write("- Player didn't bat during the selected date range")
        st.write("- Try expanding the date range")
        
        if st.button("← Start New Search", type="primary"):
            del st.session_state['data']
            st.rerun()
    
    else:
        player_id = st.session_state['batting_data']['mlbID'].iloc[0]
        
        # st.write(f"## {st.session_state['player_name']}")
        st.write(f"###### Batting stats from {st.session_state['start_date'].strftime('%B %d, %Y')}"
                 f" to {st.session_state['end_date'].strftime('%B %d, %Y')}")

        # Player bio header
        col_left, col1, col2, col3, col_right = st.columns([0.5, 1, 1, 1, 0.5])

        # Display player img
        with col1:
            st.image(player_headshot(player_id), width=200)

        # Player info
        with col2:
            st.write(f"**{st.session_state['bio']['name']}** #{st.session_state['bio']['number']}")
            st.write(f"{st.session_state['bio']['team']} • {st.session_state['bio']['position']}")
            st.write(f"Age: {st.session_state['bio']['age']} | Bats: {st.session_state['bio']['bats']} | Throws: {st.session_state['bio']['throws']}")
            st.write(f"Height: {st.session_state['bio']['height']} | Weight: {st.session_state['bio']['weight']} lbs")

        # Team logo
        with col3:
            st.image(team_logo(player_id), width = 200)

        st.write("---")

        # Batting statistics
        load_stats(st.session_state['batting_data'])

        col1, col2 = st.columns([1, 1])

        with col1:
            "### xwOBA"
            st.altair_chart(xwOBA_graph(player_data))

        with col2:
            st.pyplot(spray_chart(player_data))

        st.write("---")

        # Chase rate
        col1, col2 = st.columns([2, 1])

        with col1:
            chase_rate(player_data)

        with col2:
            zone_avgs = calculate_zone_batting_average(player_data)
            heat_map(zone_avgs)

        st.write("---")

        # splits visualizations
        col1, col2 = st.columns([1, 1])
        platoon_df = get_platoon_splits(player_data)

        with col1:
            st.write("### Clutch Splits by OPS")
            clutch_splits = get_clutch_splits(player_data)
            st.altair_chart(plot_ops_by_split(clutch_splits))

        with col2:
            st.altair_chart(create_platoon_radar_chart(platoon_df))

        col1, col2 = st.columns([2, 1])
        splits_df = get_count_splits(player_data)
        ballpark_df = get_ballpark_splits(player_data)

        with col1:
            st.altair_chart(create_count_heatmap(splits_df))

        with col2:
            display_best_ballpark(ballpark_df)

        st.write("---")

        st.write("### Pitcher vs Batter Matchup Analysis")
        st.write("Analyze how this batter performs against specific pitchers")

        pitcher_matchup(player_data)
        
        st.dataframe(get_count_splits(player_data))