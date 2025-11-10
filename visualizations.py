import altair as alt
import pandas as pd
import numpy as np
import streamlit as st
from scipy import interpolate
from pybaseball import spraychart
from utils import categorize_count

def xwOBA_graph(data, max_rolling=100): 
    """Graph a line chart with PAs rolling with xwOBA
    
    data:
        statcast batting data for a specified date and player
    max_rolling:
        maximum rolling window size (default 100, adjusts if fewer PAs available)
    """ 
    contact_events = ['single', 'double', 'triple', 'home_run', 
                    'field_out', 'grounded_into_double_play', 
                    'double_play', 'field_error', 'force_out',
                    'fielders_choice', 'fielders_choice_out',
                    'sac_fly', 'sac_bunt']

    valid_pa = data[data['woba_denom'] == 1].copy()
    valid_pa['game_date'] = pd.to_datetime(valid_pa['game_date'])
    valid_pa = valid_pa.sort_values('game_date').reset_index(drop=True)

    valid_pa['xwoba_value'] = valid_pa.apply(
        lambda row: row['estimated_woba_using_speedangle'] 
                    if pd.notna(row['estimated_woba_using_speedangle']) 
                    else row['woba_value'], 
        axis=1
    )

    # Determine actual rolling window based on available data
    total_pas = len(valid_pa)
    actual_rolling = min(max_rolling, total_pas)
    min_periods = max(10, int(actual_rolling * 0.2))  # At least 10 or 20% of window
    
    # PRE-CALCULATE rolling average on the FULL dataset
    valid_pa['rolling_xwoba'] = valid_pa['xwoba_value'].rolling(
        window=actual_rolling, 
        min_periods=min_periods
    ).mean()

    # Get overall xwOBA
    xwoba = valid_pa['xwoba_value'].mean()

    # Get the most recent PAs (up to max_rolling)
    num_recent = min(actual_rolling, total_pas)
    recent_pas = valid_pa.tail(num_recent).copy()
    recent_pas = recent_pas.reset_index(drop=True)
    recent_pas['pa_number'] = range(len(recent_pas))
    
    # Format the date for each PA with ordinal suffix
    def format_date_with_ordinal(d):
        day = d.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return d.strftime(f'%b {day}{suffix}')
    
    recent_pas['formatted_date'] = recent_pas['game_date'].apply(format_date_with_ordinal)
    
    # Format xwOBA display value (e.g., ".489")
    recent_pas['xwoba_display'] = recent_pas['rolling_xwoba'].apply(
        lambda x: f'.{int(x*1000):03d}' if pd.notna(x) else ''
    )
    
    # Create combined text for better centering
    recent_pas['xwoba_line'] = 'xwOBA: ' + recent_pas['xwoba_display']
    recent_pas['date_line'] = 'Last PA: ' + recent_pas['formatted_date']

    # Create DENSELY interpolated data for ultra-smooth tracking
    pa_numbers = recent_pas['pa_number'].values
    rolling_xwoba_values = recent_pas['rolling_xwoba'].values
    
    # Remove any NaN values for interpolation
    valid_mask = ~np.isnan(rolling_xwoba_values)
    pa_numbers_clean = pa_numbers[valid_mask]
    rolling_xwoba_clean = rolling_xwoba_values[valid_mask]
    
    # Create cubic spline interpolation for smooth curve
    if len(pa_numbers_clean) > 3:
        cs = interpolate.CubicSpline(pa_numbers_clean, rolling_xwoba_clean)
        
        # Create very dense points (20x more points for ultra-smooth tracking)
        dense_pa = np.linspace(pa_numbers_clean[0], pa_numbers_clean[-1], len(pa_numbers_clean) * 20)
        dense_xwoba = cs(dense_pa)
        
        # Create interpolated dataframe
        interpolated_data = []
        for i, (pa, xwoba_val) in enumerate(zip(dense_pa, dense_xwoba)):
            # Find nearest original PA
            nearest_idx = np.argmin(np.abs(pa_numbers - pa))
            
            interpolated_data.append({
                'pa_number': pa,
                'rolling_xwoba': xwoba_val,
                'original_pa': int(pa_numbers[nearest_idx]),
                'formatted_date': recent_pas.iloc[nearest_idx]['formatted_date'],
                'xwoba_display': recent_pas.iloc[nearest_idx]['xwoba_display'],
                'xwoba_line': recent_pas.iloc[nearest_idx]['xwoba_line'],
                'date_line': recent_pas.iloc[nearest_idx]['date_line']
            })
        
        interpolated_df = pd.DataFrame(interpolated_data)
    else:
        # Fallback if not enough points
        interpolated_df = recent_pas.copy()

    # Create a selection based on mouse x position
    mouse_selection = alt.selection_point(
        fields=['pa_number'],
        nearest=True,
        on='mouseover',
        empty='none',
        clear='mouseout'
    )

    # Create the main line chart
    line_chart = alt.Chart(recent_pas).mark_line(
        size=3,
        color='#e53935',
        interpolate='monotone',
        clip=True
    ).encode(
        x=alt.X('pa_number:Q', 
                title=None,
                scale=alt.Scale(domain=[0, len(recent_pas)-1]),
                axis=alt.Axis(
                    grid=False,
                    domain=False,
                    ticks=False,
                    labels=False
                )),
        y=alt.Y('rolling_xwoba:Q', 
                title=None,
                scale=alt.Scale(domain=[0.200, 0.700]),
                axis=alt.Axis(
                    grid=True,
                    gridDash=[2, 2],
                    gridColor='#d0d0d0',
                    tickCount=6,
                    format='.3f',
                    labelFontSize=11,
                    labelColor='#666666',
                    domain=False,
                    ticks=False
                ))
    )

    # Create a transparent RULE that covers the entire chart vertically
    selector_rules = alt.Chart(interpolated_df).mark_rule(
        opacity=0,
        size=2
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        tooltip=alt.value(None)
    ).add_params(mouse_selection)

    # Draw point on the line
    points = alt.Chart(interpolated_df).mark_point(
        size=100,
        filled=True,
        color='#e53935'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0)),
        tooltip=alt.value(None)
    ).transform_filter(mouse_selection)

    # Info box background
    info_box = alt.Chart(interpolated_df).mark_rect(
        color='#f5f5f5',
        opacity=0.95,
        stroke='#999999',
        strokeWidth=1.5,
        cornerRadius=2
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(0.95), alt.value(0))
    ).transform_calculate(
        box_left='datum.pa_number - 8',
        box_right='datum.pa_number + 8',
        box_top='datum.rolling_xwoba - 0.012',
        box_bottom='datum.rolling_xwoba - 0.072'
    ).encode(
        x=alt.X('box_left:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        x2=alt.X2('box_right:Q'),
        y=alt.Y('box_top:Q'),
        y2=alt.Y2('box_bottom:Q')
    ).transform_filter(mouse_selection)

    # First line of text - centered "xwOBA: .XXX"
    xwoba_text_line = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=27,
        fontSize=11,
        fontWeight='normal',
        color='#333333'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        y='rolling_xwoba:Q',
        text=alt.condition(mouse_selection, alt.Text('xwoba_line:N'), alt.value(' ')),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0))
    ).transform_filter(mouse_selection)

    # Second line of text - centered "Last PA: MMM DD"
    date_text_line = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=41,
        fontSize=11,
        fontWeight='normal',
        color='#666666'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_pas)-1])),
        y='rolling_xwoba:Q',
        text=alt.condition(mouse_selection, 'date_line:N', alt.value(' ')),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0))
    ).transform_filter(mouse_selection)

    # Create league average line
    league_avg_line = alt.Chart(pd.DataFrame({'y': [0.324]})).mark_rule(
        strokeDash=[3, 3],
        color='#999999',
        size=1.5,
        opacity=0.8
    ).encode(
        y='y:Q'
    )

    # Add "LG AVG" text label
    league_avg_text = alt.Chart(pd.DataFrame({
        'x': [len(recent_pas) - 1], 
        'y': [0.312], 
        'text': ['LG AVG']
    })).mark_text(
        align='right',
        dx=-5,
        dy=-8,
        color='#999999',
        fontSize=10,
        fontWeight=400
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        text='text:N'
    )

    # Combine all elements
    chart = (line_chart + selector_rules + points + info_box + 
             xwoba_text_line + date_text_line +
             league_avg_line + league_avg_text).properties(
        width=700,
        height=400
    ).configure_view(
        strokeWidth=0,
        fill='white'
    ).configure_axis(
        titleFontSize=0
    )

    return chart


def spray_chart(data):
    """Render spray chart"""
    # Filter data for hits
    hits = ['single', 'double', 'triple', 'home_run']
    data_filtered = data[data['events'].isin(hits)]

    ax = spraychart(data_filtered, 'yankees', title = 'Spray chart')
    fig = ax.get_figure()
    
    return fig

def chase_rate(df):
    """Calculates and creates chase rate analysis"""
    player_data_copy = df.copy()
    player_data_copy['in_zone'] = player_data_copy['zone'].apply(lambda x: x <= 9 if pd.notna(x) else None)

    # Identify swings
    swing_descriptions = ['swinging_strike', 'swinging_strike_blocked', 'foul', 'foul_tip', 
                          'hit_into_play', 'hit_into_play_score', 'hit_into_play_no_out',
                          'foul_bunt', 'missed_bunt', 'swinging_pitchout']
    
    player_data_copy['swung'] = player_data_copy['description'].isin(swing_descriptions)
    
    # Create count categories
    player_data_copy['count_situation'] = player_data_copy.apply(categorize_count, axis=1)

    total_pitches_out = len(player_data_copy[player_data_copy['in_zone'] == False])
    swings_out = len(player_data_copy[(player_data_copy['in_zone'] == False) & (player_data_copy['swung'] == True)])
    
    total_pitches_in = len(player_data_copy[player_data_copy['in_zone'] == True])
    swings_in = len(player_data_copy[(player_data_copy['in_zone'] == True) & (player_data_copy['swung'] == True)])
    
    chase_rate = (swings_out / total_pitches_out * 100) if total_pitches_out > 0 else 0
    zone_swing_rate = (swings_in / total_pitches_in * 100) if total_pitches_in > 0 else 0

    # Calculate overall chase rates
    st.write("### Overall Discipline Metrics")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Chase Rate", f"{chase_rate:.1f}%", 
                 help="How often batter swings at pitches outside the zone")
    
    with col2:
        st.metric("Zone Swing Rate", f"{zone_swing_rate:.1f}%",
                 help="How often batter swings at pitches in the zone")
    
    with col3:
        mlb_avg_chase = 28.0
        delta = chase_rate - mlb_avg_chase
        st.metric("vs MLB Avg (~28%)", f"{delta:+.1f}%",
                 delta=f"{delta:.1f}%",
                 delta_color="inverse")
        
    # Chase rate by count situation
    st.write("### Chase Rate by Count Situation")
    
    situations = ['Hitter ahead', 'Pitcher ahead', '2-strike (pressure)']
    chase_data = []
    
    for situation in situations:
        situation_data = player_data_copy[player_data_copy['count_situation'] == situation]
        out_zone = situation_data[situation_data['in_zone'] == False]
        chase_swings = len(out_zone[out_zone['swung'] == True])
        total_out = len(out_zone)
        
        if total_out > 0:
            rate = chase_swings / total_out * 100
        else:
            rate = 0
        
        chase_data.append({
            'Situation': situation,
            'Chase Rate': rate,
            'Label': f"{situation}\n({chase_swings}/{total_out})",
            'Count': f"({chase_swings}/{total_out})"
        })
    
    # Create DataFrame for Altair
    chart_df = pd.DataFrame(chase_data)
    
    # Define colors for each situation
    color_scale = alt.Scale(
        domain=['Hitter ahead', 'Pitcher ahead', '2-strike (pressure)'],
        range=['green', 'orange', 'red']
    )
    
    # Create base bars
    bars = alt.Chart(chart_df).mark_bar(
        opacity=0.7,
        stroke='black',
        strokeWidth=2
    ).encode(
        x=alt.X('Label:N', title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Chase Rate:Q', title='Chase Rate (%)', scale=alt.Scale(domain=[0, max(chart_df['Chase Rate']) * 1.2 if len(chart_df) > 0 else 50])),
        color=alt.Color('Situation:N', scale=color_scale, legend=None)
    )
    
    # Add value labels on bars
    text = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-5,
        fontSize=14,
        fontWeight='bold'
    ).encode(
        text=alt.Text('Chase Rate:Q', format='.1f'),
        color=alt.value('black')
    )
    
    # Add MLB average line
    mlb_avg_chase = 28.0
    rule = alt.Chart(pd.DataFrame({'y': [mlb_avg_chase]})).mark_rule(
        color='blue',
        strokeDash=[5, 5],
        strokeWidth=2
    ).encode(
        y='y:Q'
    )
    
    # Add label for the rule
    rule_label = rule.mark_text(
        align='right',
        dx=-5,
        dy=-5,
        text='MLB Average (~28%)',
        fontSize=11,
        color='blue'
    )
    
    # Combine all layers
    chart = (bars + text + rule + rule_label).properties(
        width=600,
        height=400,
        title=f'{st.session_state["player_name"]} - Chase Rate by Count Situation'
    ).configure_axis(
        grid=True,
        gridOpacity=0.3
    ).configure_title(
        fontSize=14,
        fontWeight='bold',
        anchor='start'
    )
    
    st.altair_chart(chart, use_container_width=True)

def heat_map(df):
    # Detect batting average column name
    possible_cols = ['batting_avg', 'avg', 'batting_average', 'BA']
    avg_col = next((col for col in possible_cols if col in df.columns), None)

    if avg_col is None:
        st.error(f"No batting average column found in DataFrame. Columns: {list(df.columns)}")
        return

    df = df.copy()
    df["batting_avg_label"] = df[avg_col].round(3)

    # Define explicit category orders so the zone grid maps correctly to visual rows/cols
    # Adjust these lists if your data uses different category names
    x_order = ['Left', 'Middle', 'Right']
    y_order = ['High', 'Mid', 'Low']   # top -> bottom: High, Mid, Low

    # Create the heatmap with red-blue color scheme (blue = low, red = high)
    heatmap = alt.Chart(df).mark_rect(stroke='black', strokeWidth=2).encode(
        x=alt.X("plate_x:O",
                sort=x_order,
                title="Horizontal Distance (Catcher Perspective) [ft]",
                axis=alt.Axis(labelFontSize=14, titleFontSize=14, titleFontWeight='bold')),
        y=alt.Y("plate_z:O",
                sort=y_order,
                title="Vertical Distance (Above Home Plate) [ft]",
                axis=alt.Axis(labelFontSize=14, titleFontSize=14, titleFontWeight='bold')),
        color=alt.Color(
            f"{avg_col}:Q",
            title="Batting Average",
            scale=alt.Scale(
                scheme="redblue",  # Red for high, blue for low
                domain=[0, 0.5],
                reverse=True  # Reverse so red is high, blue is low
            ),
            legend=alt.Legend(titleFontSize=13, labelFontSize=12, titleFontWeight='bold')
        ),
        tooltip=[
            alt.Tooltip("plate_x:O", title="X Zone"),
            alt.Tooltip("plate_z:O", title="Z Zone"),
            alt.Tooltip(f"{avg_col}:Q", title="Batting Average", format=".3f")
        ]
    )

    # Add text labels using the same ordering
    text = alt.Chart(df).mark_text(
        align="center",
        baseline="middle",
        fontSize=18,
        fontWeight="bold"
    ).encode(
        x=alt.X("plate_x:O", sort=x_order),
        y=alt.Y("plate_z:O", sort=y_order),
        text=alt.Text("batting_avg_label:Q", format=".3f"),
        color=alt.condition(
            f"datum.{avg_col} > 0.25",  # Adjust threshold for text color
            alt.value("white"),
            alt.value("black")
        )
    )

    # Combine layers and set strike zone proportions
    chart = (
        (heatmap + text)
        .properties(
            width=450,   # Width for strike zone (17 inches = ~1.4 feet)
            height=600,  # Height to match typical strike zone ratio
            title={
                'text': f"{st.session_state.get('player_name', 'Player')} - Batting Average by Zone",
                'fontSize': 18,
                'fontWeight': 'bold',
                'anchor': 'middle'
            }
        )
        .configure_view(
            stroke='black',
            strokeWidth=2,
            fill='#f9f9f9'
        )
    )

    st.altair_chart(chart, use_container_width=False)
