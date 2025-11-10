import streamlit as st
import pandas as pd
from streamlit_searchbox import st_searchbox
import warnings

warnings.filterwarnings('ignore', module='pybaseball.plotting')

# Import modules
from player_search import search_players, get_player_full_name
from data_loader import load_statcast_data, load_batting_stats
from player_bio import (
    player_bio, player_headshot, team_logo, 
    load_stats, load_stats_compact
)
from visualizations import xwOBA_graph, spray_chart, chase_rate, heat_map
from utils import calculate_zone_batting_average
from matchup import pitcher_matchup
from splits import get_platoon_splits, get_clutch_splits, get_count_splits, get_ballpark_splits
from splits_visualizations import (
    plot_ops_by_split, create_platoon_radar_chart, 
    create_count_heatmap, display_best_ballpark
)

# Constants
MIN_STATCAST_DATE = pd.to_datetime('2015-04-01')
MAX_STATCAST_DATE = pd.to_datetime('2025-11-15')

# App configuration
st.set_page_config(
    page_title="MLB Batter Analysis",
    layout='wide'
)


def is_mobile():
    """Check if on mobile via query params for testing"""
    query_params = st.query_params
    return 'mobile' in query_params and query_params['mobile'].lower() == 'true'


def render_page_header():
    """Render the main page header with title and description"""
    st.markdown(
        "<h1 style='text-align: center;'>MLB Batter Analysis</h1>", 
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 14px;'>"
        "Analyze MLB player performance with Statcast data (2015-present). "
        "View rolling stats, spray charts, chase rates, situational splits, "
        "zone heatmaps, and pitcher matchup history."
        "</p>",
        unsafe_allow_html=True
    )


def validate_inputs(player_name, start_date, end_date):
    """
    Validate user inputs for player selection and date range.
    
    Returns:
    --------
    tuple : (is_valid, error_messages)
    """
    errors = []
    
    if not player_name and start_date is None or end_date is None:
        errors.append("Please select a player and both start and end dates")
    elif start_date > end_date:
        errors.append("Start date must be before end date")
    
    return len(errors) == 0, errors


def render_initial_search_form():
    """Render the initial player search form when no data is loaded"""
    st.markdown("---")
    st.markdown(
        "<h3 style='text-align: center;'>Get Started</h3>", 
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 14px;'>"
        "Statcast data available from 2015-present, select a player and date range to begin analysis"
        "</p>",
        unsafe_allow_html=True
    )

    st.markdown(
    "<p style='text-align: center; color: gray; font-size: 14px;'>"
    "Larger date searches may take a moment to load"
    "</p>",
    unsafe_allow_html=True
)

    # Initialize session state for search term if needed
    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = None

    # Create layout columns
    col_spacer1, col1, col2, col3, col_spacer2 = st.columns([0.5, 3, 2, 2, 0.5])

    # Player search box
    with col1:
        selected_player_display = st_searchbox(
            search_players,
            label="Batter Name",
            placeholder="Start typing a player name...",
            clear_on_submit=False,
            key="player_searchbox",
            default=st.session_state.get('search_term', None)
        )
        
        if selected_player_display:
            st.session_state['search_term'] = selected_player_display

        player_name = get_player_full_name(selected_player_display)

        if selected_player_display and not player_name:
            st.warning("Please select a valid player from the dropdown")

    # Date inputs
    with col2:
        start_date = st.date_input(
            "**Start Date**",
            value=None,
            min_value=MIN_STATCAST_DATE,
            max_value=MAX_STATCAST_DATE,
            help="Statcast era: 2015-present",
            key="main_start_date"
        )

    with col3:
        end_date = st.date_input(
            "**End Date**",
            value=None,
            min_value=MIN_STATCAST_DATE,
            max_value=MAX_STATCAST_DATE,
            help="Select the end date for analysis",
            key="main_end_date"
        )

    # Validation
    is_valid, errors = validate_inputs(player_name, start_date, end_date)
    
    if not is_valid:
        for error in errors:
            st.error(error)
    
    st.markdown("")

    # Load button
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_center:
        if st.button(
            "Load Player Data", 
            type="primary", 
            disabled=not is_valid,
            use_container_width=True
        ):
            load_player_data(player_name, start_date, end_date)


def load_player_data(player_name, start_date, end_date):
    """Load player data and store in session state"""
    with st.spinner(f"Loading data for {player_name} from {start_date} to {end_date}..."):
        try:
            batting_data = load_batting_stats(start_date, end_date, str(player_name))
            player_id = batting_data['mlbID'].iloc[0]
            bio = player_bio(player_id)
            data = load_statcast_data(start_date, end_date)
            
            # Store in session state
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


def render_quick_search_bar():
    """Render the quick search bar for switching players/dates when data is loaded"""
    st.markdown("---")
    st.write("### Change Player or Date Range")
    
    col_search, col_start, col_end, col_button = st.columns([3, 1.5, 1.5, 1])

    with col_search:
        new_selected_display = st_searchbox(
            search_players,
            label="Search Different Player:",
            placeholder="Type player name to switch...",
            clear_on_submit=False,
            key="quick_player_search"
        )
        new_player_name = get_player_full_name(new_selected_display) if new_selected_display else None

    with col_start:
        new_start_date = st.date_input(
            "**Start Date**",
            value=st.session_state['start_date'],
            min_value=MIN_STATCAST_DATE,
            max_value=MAX_STATCAST_DATE,
            key="quick_start_date"
        )
    
    with col_end:
        new_end_date = st.date_input(
            "**End Date**",
            value=st.session_state['end_date'],
            min_value=MIN_STATCAST_DATE,
            max_value=MAX_STATCAST_DATE,
            key="quick_end_date"
        )

    with col_button:
        st.markdown("")  # Spacing
        st.markdown("")  # More spacing
        
        # Check if anything changed
        player_changed = new_player_name and new_player_name != st.session_state['player_name']
        dates_changed = (new_start_date != st.session_state['start_date'] or 
                        new_end_date != st.session_state['end_date'])
        
        if st.button(
            "Load Data", 
            type="primary", 
            disabled=not (player_changed or dates_changed),
            use_container_width=True
        ):
            load_player = new_player_name if player_changed else st.session_state['player_name']
            load_player_data(load_player, new_start_date, new_end_date)


def render_player_bio_desktop(player_id, bio):
    """Render player bio in desktop layout"""
    col_left, col1, col2, col3, col_right = st.columns([0.5, 1, 1, 1, 0.5])

    with col1:
        st.image(player_headshot(player_id), width=200)

    with col2:
        st.write(f"**{bio['name']}** #{bio['number']}")
        st.write(f"{bio['team']} • {bio['position']}")
        st.write(f"Age: {bio['age']} | Bats: {bio['bats']} | Throws: {bio['throws']}")
        st.write(f"Height: {bio['height']} | Weight: {bio['weight']} lbs")

    with col3:
        st.image(team_logo(player_id), width=200)


def render_player_bio_mobile(player_id, bio):
    """Render player bio in mobile layout"""
    st.write(f"### {st.session_state['player_name']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(player_headshot(player_id), width=120)
    
    with col2:
        st.write(f"**#{bio['number']}** • {bio['position']}")
        st.write(f"{bio['team']}")
        st.write(f"Age {bio['age']} • {bio['bats']}/{bio['throws']}")
        st.write(f"{bio['height']} • {bio['weight']} lbs")
    
    st.write("---")
    st.write("### Statistics")


def render_visualizations(player_data, batting_data, player_name, start_date, end_date):
    """Render all player visualizations and analysis"""
    
    # xwOBA and Spray Chart
    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("### xwOBA Rolling by PA")
        st.altair_chart(xwOBA_graph(player_data), use_container_width=True)
        st.markdown("""
        ### xwOBA (Expected Weighted On-Base Average)
        Estimates how a hitter *should* perform based on contact quality — using exit velocity, launch angle, walks, and strikeouts — instead of luck or defense.

        **League Avg:** ~.320  
        **Good:** .370+  
        **Below Avg:** <.290  

        _Shows a player's true offensive skill per plate appearance._
        """)

    with col2:
        st.pyplot(spray_chart(player_data))

    st.write("---")

    # Chase rate and zone heat map
    col1, col2 = st.columns([2, 1])

    with col1:
        chase_rate(player_data)

    with col2:
        zone_avgs = calculate_zone_batting_average(player_data)
        heat_map(zone_avgs)

    st.write("---")

    # Splits visualizations
    col1, col2 = st.columns([1, 1])
    platoon_df = get_platoon_splits(player_data)

    with col1:
        st.write("### Clutch Splits by OPS")
        clutch_splits = get_clutch_splits(player_data)
        st.altair_chart(plot_ops_by_split(clutch_splits), use_container_width=True)

    with col2:
        st.altair_chart(create_platoon_radar_chart(platoon_df), use_container_width=True)

    col1, col2 = st.columns([2, 1])
    splits_df = get_count_splits(player_data)
    ballpark_df = get_ballpark_splits(player_data)

    with col1:
        st.altair_chart(create_count_heatmap(splits_df), use_container_width=True)

    with col2:
        st.markdown(f"""
        <div style="
            text-align:center;
            padding:8px 0;
            margin-bottom:8px;
        ">
            <h4 style="margin-bottom:0; font-size:18px;">
                From <b>{start_date}</b> to <b>{end_date}</b>,
            </h4>
            <h4 style="margin-top:4px; font-size:18px;">
                <b>{player_name}</b> performed the best at:
            </h4>
        </div>
        """, unsafe_allow_html=True)

        display_best_ballpark(ballpark_df)

    st.write("---")

    # Pitcher matchup analysis
    st.write("### Pitcher vs Batter Matchup Analysis")
    st.write("Analyze how this batter performs against specific pitchers")
    pitcher_matchup(player_data)


def main():
    """Main application logic"""
    render_page_header()
    
    # Check if data is loaded
    if 'data' not in st.session_state:
        render_initial_search_form()
    else:
        render_quick_search_bar()
        
        # Filter to player data
        player_data = st.session_state['data'][
            st.session_state['data']['batter_name'] == st.session_state['player_name']
        ]

        batting_data = st.session_state['batting_data']
        
        # Check if player has data in range
        if len(player_data) == 0:
            st.error(f"No data found for **{st.session_state['player_name']}**")
            st.write("**Possible reasons:**")
            st.write("- Player didn't bat during the selected date range")
            st.write("- Try expanding the date range")
            
            if st.button("← Start New Search", type="primary"):
                del st.session_state['data']
                st.rerun()
        else:
            # Display player info and stats
            player_id = st.session_state['batting_data']['mlbID'].iloc[0]
            start_date_str = st.session_state['start_date'].strftime('%B %d, %Y')
            end_date_str = st.session_state['end_date'].strftime('%B %d, %Y')
            
            st.write(f"###### Batting stats from {start_date_str} to {end_date_str}")

            # Conditional rendering based on mobile/desktop
            mobile_view = is_mobile()

            if mobile_view:
                render_player_bio_mobile(player_id, st.session_state['bio'])
                load_stats_compact(batting_data)
            else:
                render_player_bio_desktop(player_id, st.session_state['bio'])
                st.write("---")
                load_stats(batting_data)

            st.write("---")

            # Render all visualizations
            render_visualizations(
                player_data, 
                batting_data, 
                st.session_state['player_name'],
                start_date_str,
                end_date_str
            )


if __name__ == "__main__":
    main()