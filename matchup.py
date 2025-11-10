"""Pitcher vs Batter matchup analysis"""

import streamlit as st
import pandas as pd
import altair as alt
from pybaseball.plotting import plot_strike_zone
from utils import count_at_bats

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

    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_pitches = len(matchup_data)
    at_bats = count_at_bats(matchup_data)
    
    # Count outcomes
    outcomes = matchup_data[matchup_data['events'].notna()]
    strikeouts = len(outcomes[outcomes['events'].str.contains('strikeout', na=False)])
    walks = len(outcomes[outcomes['events'].str.contains('walk', na=False)])
    hits = len(outcomes[outcomes['events'].isin(['single', 'double', 'triple', 'home_run'])])
    
    with col1:
        st.metric("Total Pitches", total_pitches)
    with col2:
        st.metric("At-Bats", at_bats)
    with col3:
        st.metric("Strikeouts", strikeouts)
    with col4:
        st.metric("Hits", hits)
    with col5:
        st.metric("Walks", walks)

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
            
            # Add percentage labels with better positioning
            text = pie_chart.mark_text(
                radiusOffset=30,  # Push labels outside the pie
                fontSize=13,
                fontWeight='bold',
                color='black'
            ).encode(
                text='Label:N'
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
            
            if len(matchup_outs) > 0:
                try:
                    ax = plot_strike_zone(
                        matchup_outs,
                        title=f"Out Locations\n({len(matchup_outs)} outs)",
                        colorby='pitch_type',
                        annotation=None
                    )

                    fig = ax.get_figure()
                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"Error creating plot: {e}")
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
                            
                            # Let plot_strike_zone create the plot
                            ax = plot_strike_zone(single_pitch, title=title, 
                                                colorby='pitch_type', annotation='release_speed')
                            
                            # Get the figure from the axes
                            fig = ax.get_figure()
                            
                            # Display in this column
                            st.pyplot(fig)
                            
                            pitch_num += 1