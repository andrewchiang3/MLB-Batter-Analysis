import streamlit as st
import pandas as pd
from streamlit_searchbox import st_searchbox
import warnings
import streamlit.components.v1 as components
warnings.filterwarnings('ignore', module='pybaseball.plotting')

# Modules
from player_search import search_players, get_player_full_name
from data_loader import load_statcast_data, load_batting_stats
from player_bio import *
from visualizations import *
from utils import calculate_zone_batting_average
from matchup import pitcher_matchup
from splits import *
from splits_visualizations import *

# Function to get screen width
def get_screen_width():
    """Inject JavaScript to get screen width and store in session state"""
    js_code = """
    <script>
        var width = window.innerWidth;
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: width}, '*');
    </script>
    """
    width = components.html(js_code, height=0)
    return width

# Initialize screen width in session state
if 'screen_width' not in st.session_state:
    st.session_state['screen_width'] = get_screen_width()

# Detect if mobile (width < 768px is typical mobile breakpoint)
def is_mobile():
    width = st.session_state.get('screen_width', 1200)
    return width is not None and width < 768

# App configuration
st.set_page_config(
    page_title = "MLB Batter Analysis",
    layout = 'wide'
)

# Get screen width on first load
if 'screen_width' not in st.session_state:
    # Use a more reliable method with streamlit-javascript
    st.session_state['screen_width'] = None

# Add hidden div to capture screen width
components.html(
    """
    <script>
        const width = window.innerWidth;
        const streamlitDoc = window.parent.document;
        const statusElements = streamlitDoc.querySelectorAll('[data-testid="stStatusWidget"]');
        if (statusElements.length > 0) {
            statusElements[0].textContent = width;
        }
        // Send message to Streamlit
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: width
        }, '*');
    </script>
    """,
    height=0
)

def is_mobile():
    """Check if on mobile - you can adjust this manually or detect via query params"""
    # Simple approach: check if layout is set to wide
    # In practice, we'll use a simpler heuristic
    # For now, let's add a toggle or use a default assumption
    return st.session_state.get('force_mobile', False)

# Add a hidden parameter to force mobile view (for testing)
# You can set this via URL: ?mobile=true
query_params = st.query_params
if 'mobile' in query_params:
    st.session_state['force_mobile'] = query_params['mobile'].lower() == 'true'

# Main page layout
st.markdown("<h1 style='text-align: center;'>MLB Batter Analysis</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 14px;'>"
    "Analyze MLB player performance with Statcast data (2015-present). "
    "View rolling stats, spray charts, chase rates, situational splits, "
    "zone heatmaps, and pitcher matchup history."
    "</p>",
    unsafe_allow_html=True
)

# Check if data is loaded
if 'data' not in st.session_state:
    # Main page when no data is loaded
    st.markdown("---")
    st.markdown("<h3 style='text-align: center;'>Get Started</h1>", unsafe_allow_html=True)
    st.markdown(
    "<p style='text-align: center; color: gray; font-size: 14px;'>"
    "Statcast data available from 2015-present, select a player and date range to begin analysis"
    "</p>",
    unsafe_allow_html=True
)

    # Initialize search term in session state to prevent reset
    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = None
    
    # Initialize date defaults
    if 'temp_start' not in st.session_state:
        st.session_state['temp_start'] = None
    if 'temp_end' not in st.session_state:
        st.session_state['temp_end'] = None

    # Columns for more compact layout
    col_spacer1, col1, col2, col3, col_spacer2 = st.columns([0.5, 3, 2, 2, 0.5])

    # Player search box
    with col1:
        # Use searchbox for autocomplete with default value from session state
        selected_player_display = st_searchbox(
            search_players,
            label = "Batter Name",
            placeholder = "Start typing a player name...",
            clear_on_submit = False,
            key = "player_searchbox",
            default = st.session_state.get('search_term', None)
        )
        
        # Store search term to prevent reset
        if selected_player_display:
            st.session_state['search_term'] = selected_player_display

        # Get actual name from display name
        player_name = get_player_full_name(selected_player_display)

        if selected_player_display and not player_name:
            st.warning("Please select a valid player from the dropdown")

    # Date input - blank by default unless season selected
    with col2:
        start_date = st.date_input(
            "**Start Date**",
            value=st.session_state['temp_start'],
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            help="Statcast era: 2015-present",
            key="main_start_date"
        )

    with col3:
        end_date = st.date_input(
            "**End Date**",
            value=st.session_state['temp_end'],
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            help="Select the end date for analysis",
            key="main_end_date"
        )

    # Validation
    validation_errors = []
    if not player_name and start_date is None or end_date is None:
        validation_errors.append("Please select a player and both start and end dates")
    elif start_date > end_date:
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
                    
                    # Clear temp dates
                    if 'temp_start' in st.session_state:
                        del st.session_state['temp_start']
                    if 'temp_end' in st.session_state:
                        del st.session_state['temp_end']
                    
                    st.success(f"Successfully loaded {len(data):,} pitches!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error loading data: {e}")

# Data is already loaded, switch if user wants to
else:
    player_name = st.session_state['player_name']
    st.markdown("---")

    # Quick search bar at the top with date options
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
            value=st.session_state.get('quick_temp_start', st.session_state['start_date']),
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            key="quick_start_date"
        )
    
    with col_end:
        new_end_date = st.date_input(
            "**End Date**",
            value=st.session_state.get('quick_temp_end', st.session_state['end_date']),
            min_value=pd.to_datetime('2015-04-01'),
            max_value=pd.to_datetime('2025-11-15'),
            key="quick_end_date"
        )

    with col_button:
        st.markdown("")  # Spacing to align with date inputs
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
            # Determine what to update
            load_player = new_player_name if player_changed else st.session_state['player_name']
            load_start = new_start_date
            load_end = new_end_date
            
            # Update session state
            st.session_state['player_name'] = load_player
            st.session_state['start_date'] = load_start
            st.session_state['end_date'] = load_end
            
            # Load new data
            with st.spinner(f"Loading data for {load_player}..."):
                try:
                    new_batting_data = load_batting_stats(load_start, load_end, load_player)
                    new_player_id = new_batting_data['mlbID'].iloc[0]
                    new_data = load_statcast_data(load_start, load_end)
                    bio = player_bio(new_player_id)
                    
                    # Update with new data
                    st.session_state['bio'] = bio
                    st.session_state['data'] = new_data
                    st.session_state['batting_data'] = new_batting_data
                    
                    # Clear temp dates
                    if 'quick_temp_start' in st.session_state:
                        del st.session_state['quick_temp_start']
                    if 'quick_temp_end' in st.session_state:
                        del st.session_state['quick_temp_end']
                    
                    st.success(f"Loaded {len(new_data):,} pitches for {load_player}!")
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
        start_date = st.session_state['start_date'].strftime('%B %d, %Y')
        end_date = st.session_state['end_date'].strftime('%B %d, %Y')
    
        st.write(f"###### Batting stats from {start_date} to {end_date}")

        # CONDITIONAL RENDERING BASED ON SCREEN SIZE
        mobile_view = is_mobile()

        if mobile_view:
            # ========== MOBILE LAYOUT ==========
            st.write(f"### {st.session_state['player_name']}")
            
            # Compact player bio
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(player_headshot(player_id), width=120)
            
            with col2:
                st.write(f"**#{st.session_state['bio']['number']}** • {st.session_state['bio']['position']}")
                st.write(f"{st.session_state['bio']['team']}")
                st.write(f"Age {st.session_state['bio']['age']} • {st.session_state['bio']['bats']}/{st.session_state['bio']['throws']}")
                st.write(f"{st.session_state['bio']['height']} • {st.session_state['bio']['weight']} lbs")
            
            st.write("---")
            
            # Compact stats table instead of metrics
            st.write("### Statistics")
            load_stats_compact(st.session_state['batting_data'])
            
        else:
            # ========== DESKTOP LAYOUT ==========
            # Player bio header with larger images
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
                st.image(team_logo(player_id), width=200)

            st.write("---")

            # Full batting statistics with metrics
            load_stats(st.session_state['batting_data'])

        st.write("---")

        # Rest of visualizations remain the same
        col1, col2 = st.columns([1, 1])

        with col1:
            "### xwOBA Rolling by PA"
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

        st.write("### Pitcher vs Batter Matchup Analysis")
        st.write("Analyze how this batter performs against specific pitchers")

        pitcher_matchup(player_data)