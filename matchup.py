"""Pitcher vs Batter matchup analysis"""

import streamlit as st
import pandas as pd
import altair as alt
from pybaseball.plotting import plot_strike_zone
from utils import count_at_bats
import matplotlib.pyplot as plt

def pitcher_matchup(player_data):
    """Pitcher vs batter matchup"""
    # Get list of pitchers this batter has faced
    pitchers = player_data.groupby(['pitcher', 'player_name']).size().reset_index(name='pitches')
    pitchers = pitchers.sort_values('pitches', ascending=False)
    
    if len(pitchers) == 0:
        st.warning("No pitcher data available for this date range")
        return
    
    st.write(f"**Pitchers Faced:** {len(pitchers)}")
    
    # Let user select a pitcher
    pitcher_options = [
        f"{row['player_name']} ({row['pitches']} pitches)"
        for _, row in pitchers.iterrows()
    ]
    
    selected_pitcher_display = st.selectbox(
        "Select Pitcher:",
        options=pitcher_options,
        help="Choose a pitcher to analyze the matchup"
    )
    
    # Extract pitcher ID from selection
    selected_idx = pitcher_options.index(selected_pitcher_display)
    selected_pitcher_id = pitchers.iloc[selected_idx]['pitcher']
    selected_pitcher_name = pitchers.iloc[selected_idx]['player_name']
    
    # Filter data for this matchup
    matchup_data = player_data[player_data['pitcher'] == selected_pitcher_id].copy()
    
    st.write(f"## {st.session_state['player_name']} vs {selected_pitcher_name}")

    # Calculate comprehensive stats
    total_pitches = len(matchup_data)
    
    # Count outcomes
    outcomes = matchup_data[matchup_data['events'].notna()]
    
    # Calculate at-bats and hits
    at_bats = count_at_bats(matchup_data)
    hits = len(outcomes[outcomes['events'].isin(['single', 'double', 'triple', 'home_run'])])
    singles = len(outcomes[outcomes['events'] == 'single'])
    doubles = len(outcomes[outcomes['events'] == 'double'])
    triples = len(outcomes[outcomes['events'] == 'triple'])
    home_runs = len(outcomes[outcomes['events'] == 'home_run'])
    
    # Calculate walks and other outcomes
    walks = len(outcomes[outcomes['events'].str.contains('walk', na=False)])
    hbp = len(outcomes[outcomes['events'].isin(['hit_by_pitch'])])
    sac_flies = len(outcomes[outcomes['events'].isin(['sac_fly', 'sac_fly_double_play'])])
    strikeouts = len(outcomes[outcomes['events'].str.contains('strikeout', na=False)])
    
    # Calculate batting line stats
    avg = hits / at_bats if at_bats > 0 else 0
    obp = (hits + walks + hbp) / (at_bats + walks + hbp + sac_flies) if (at_bats + walks + hbp + sac_flies) > 0 else 0
    total_bases = singles + (2 * doubles) + (3 * triples) + (4 * home_runs)
    slg = total_bases / at_bats if at_bats > 0 else 0
    ops = obp + slg

    # Summary metrics - First row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Pitches", total_pitches)
    with col2:
        st.metric("Matchup Record", f"{hits}-for-{at_bats}", help="Hits vs At-Bats in this matchup")
    with col3:
        st.metric("H", hits, help=f"1B: {singles} 2B: {doubles} 3B: {triples}")
    with col4:
        st.metric("Home Runs", home_runs)
    with col5:
        st.metric("Walks", walks)
    with col6:
        st.metric("Strikeouts", strikeouts)
    
    # Batting line stats - Second row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("AVG", f"{avg:.3f}", help="Batting Average")
    with col2:
        st.metric("OBP", f"{obp:.3f}", help="On-Base Percentage")
    with col3:
        st.metric("SLG", f"{slg:.3f}", help="Slugging Percentage")
    with col4:
        st.metric("OPS", f"{ops:.3f}", help="On-Base Plus Slugging")

    st.write("### Matchup Summary")
        
    col1, col2 = st.columns(2)

    outcome_counts = outcomes['events'].value_counts()

    with col1:
    # Pie chart of outcomes
        if len(outcome_counts) > 0:
            # Prepare data for Altair
            outcome_df = outcome_counts.reset_index()
            outcome_df.columns = ['Outcome', 'Count']
            
            # Calculate percentages
            total = outcome_df['Count'].sum()
            outcome_df['Percentage'] = (outcome_df['Count'] / total * 100).round(1)
            
            # Filter out very small slices that clutter the chart
            outcome_df['Label'] = outcome_df.apply(
                lambda row: f"{row['Percentage']:.1f}%" if row['Percentage'] >= 5 else "",
                axis=1
            )
            
            # Create pie chart with better colors
            pie_chart = alt.Chart(outcome_df).mark_arc(
                stroke='white',
                strokeWidth=3,
                outerRadius=150
            ).encode(
                theta=alt.Theta('Count:Q', stack=True),
                color=alt.Color('Outcome:N', 
                            legend=alt.Legend(
                                title='Outcome', 
                                titleFontSize=13, 
                                labelFontSize=11,
                                orient='right',
                                titleFontWeight='bold'
                            )),
                tooltip=[
                    alt.Tooltip('Outcome:N', title='Outcome'),
                    alt.Tooltip('Count:Q', title='Count'),
                    alt.Tooltip('Percentage:Q', title='Percentage', format='.1f')
                ],
                order=alt.Order('Count:Q', sort='descending')  # Largest slices first
            )
            
            # Combine chart
            # Just use the pie chart without text overlay
            outcome_chart = pie_chart.properties(
                width=450,
                height=450,
                title={
                    'text': 'Outcome Distribution',
                    'fontSize': 14,
                    'fontWeight': 'bold'
                }
            )
            
            st.altair_chart(outcome_chart, use_container_width=True)

        with col2:
            st.write("**Pitches Resulting in Outs:**")
            matchup_outs = matchup_data[
                matchup_data['events'].isin([
                    'strikeout', 'strikeout_double_play', 'field_out', 
                    'force_out', 'grounded_into_double_play'
                ])
            ]
            
            # Filter out pitch types that pybaseball doesn't recognize
            # Known issue: CS (Slow Curve) and some other rare pitch types cause KeyError
            unsupported_pitch_types = ['CS', 'SC', 'UN', 'AB', 'PO']
            matchup_outs_filtered = matchup_outs[
                ~matchup_outs['pitch_type'].isin(unsupported_pitch_types)
            ]
            
            if len(matchup_outs_filtered) > 0:
                try:
                    ax = plot_strike_zone(
                        matchup_outs_filtered,
                        title=f"Out Locations\n({len(matchup_outs_filtered)} outs)",
                        colorby='pitch_type',
                        annotation=None
                    )

                    fig = ax.get_figure()
                    st.pyplot(fig)
                    
                    # Show note if we filtered out some pitches
                    filtered_count = len(matchup_outs) - len(matchup_outs_filtered)
                    if filtered_count > 0:
                        st.caption(f"Note: {filtered_count} pitch(es) with unsupported type excluded")
                except Exception as e:
                    st.error(f"Error creating plot: {e}")
            else:
                if len(matchup_outs) > 0:
                    st.info(f"All {len(matchup_outs)} outs used unsupported pitch types")
                else:
                    st.info("No outs in this matchup yet")

    st.write("### At-Bat History")
    st.write('**See pitch sequences for each at-bat**')

    # Get unique at-bats
    at_bat_groups = matchup_data.groupby(['game_pk', 'at_bat_number'])

    st.write(f"**Total At-Bats: {len(at_bat_groups)}**")

    with st.expander(f"At-bat sequences against {selected_pitcher_name}"):
        for (game_pk, at_bat_num), at_bat_data in at_bat_groups:
            at_bat_sorted = at_bat_data.sort_values('pitch_number')
            
            game_date = pd.to_datetime(at_bat_sorted.iloc[0]['game_date']).strftime('%B %d, %Y')
            outcome = at_bat_sorted.iloc[-1]['events']
            num_pitches = len(at_bat_sorted)
            
            with st.expander(f"{game_date} - {num_pitches} pitches → **{outcome}**"):
                # Show pitch details text
                st.write("**Pitch Sequence:**")
                for idx, (_, pitch) in enumerate(at_bat_sorted.iterrows(), 1):
                    count = f"{int(pitch['balls'])}-{int(pitch['strikes'])}"
                    st.write(
                        f"**Pitch {idx}:** {pitch['pitch_name']} - {count} - "
                        f"{pitch['description']} - {pitch['release_speed']:.1f} mph"
                    )
                
                st.write("---")
                st.write("**Pitch Locations:**")
                
                # Create pitch sequence visualization
                cols_per_row = min(num_pitches, 3)  # Max 3 pitches per row
                
                pitch_num = 1
                for start_idx in range(0, num_pitches, cols_per_row):
                    # Create columns for this row
                    cols = st.columns(cols_per_row)
                    
                    # Get pitches for this row
                    end_idx = min(start_idx + cols_per_row, num_pitches)
                    row_pitches = list(at_bat_sorted.iterrows())[start_idx:end_idx]
                    
                    for col_idx, (_, pitch) in enumerate(row_pitches):
                        with cols[col_idx]:
                            # Create a dataframe with just this one pitch
                            single_pitch = pitch.to_frame().T
                            
                            # Get count for title
                            count = f"{int(pitch['balls'])}-{int(pitch['strikes'])}"
                            
                            # Create title
                            title = f"Pitch #{pitch_num} - {count}\n{pitch['pitch_name']}\n{pitch['description']}"
                            if pd.notna(pitch['events']):
                                title += f"\n**{pitch['events'].upper()}**"
                            
                            # Check if this pitch type is supported by pybaseball
                            unsupported_pitch_types = ['CS', 'SC', 'UN', 'AB', 'PO']
                            pitch_type = pitch.get('pitch_type', '')
                            
                            if pitch_type in unsupported_pitch_types:
                                # Display pitch info as text for unsupported types
                                st.write(f"**{title}**")
                                st.write(f"Speed: {pitch.get('release_speed', 'N/A')} mph")
                                st.caption(f"(Pitch type '{pitch_type}' not supported in visualization)")
                            elif pd.notna(pitch.get('plate_x')) and pd.notna(pitch.get('plate_z')):
                                try:
                                    # Use pybaseball's plot_strike_zone
                                    ax = plot_strike_zone(single_pitch, title=title, 
                                                        colorby='pitch_type', annotation='release_speed')
                                    
                                    fig = ax.get_figure()
                                    st.pyplot(fig)
                                    plt.close(fig)
                                except Exception as e:
                                    # Fallback if plotting fails
                                    st.write(f"**{title}**")
                                    st.write(f"Speed: {pitch.get('release_speed', 'N/A')} mph")
                                    st.caption(f"(Error plotting: {str(e)})")
                            else:
                                # No location data available
                                st.write(f"**{title}**")
                                st.write(f"Speed: {pitch.get('release_speed', 'N/A')} mph")
                                st.caption("(Location data not available)")
                            
                            pitch_num += 1
