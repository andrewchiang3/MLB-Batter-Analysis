import altair as alt
import pandas as pd
import numpy as np
import streamlit as st
from scipy import interpolate
from pybaseball import spraychart
from utils import categorize_count

def xwOBA_graph(data): 
    """Graph a line chart with PAs rolling with xwOBA
    
    data:
        statcast batting data for a specified date and player
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

    # PRE-CALCULATE rolling average on the FULL dataset
    valid_pa['rolling_xwoba'] = valid_pa['xwoba_value'].rolling(window=100, min_periods=20).mean()

    # Get overall xwOBA and last PA date
    xwoba = valid_pa['xwoba_value'].mean()

    # Get the most recent 100 PAs
    recent_100 = valid_pa.tail(100).copy()
    recent_100 = recent_100.reset_index(drop=True)
    recent_100['pa_number'] = range(len(recent_100))
    
    # Format the date for each PA with ordinal suffix
    def format_date_with_ordinal(d):
        day = d.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return d.strftime(f'%b {day}{suffix}')
    
    recent_100['formatted_date'] = recent_100['game_date'].apply(format_date_with_ordinal)
    
    # Format xwOBA display value (e.g., ".489")
    recent_100['xwoba_display'] = recent_100['rolling_xwoba'].apply(
        lambda x: f'.{int(x*1000):03d}' if pd.notna(x) else ''
    )
    
    # Create combined text for better centering
    recent_100['xwoba_line'] = 'xwOBA: ' + recent_100['xwoba_display']
    recent_100['date_line'] = 'Last PA: ' + recent_100['formatted_date']

    # Create DENSELY interpolated data for ultra-smooth tracking
    pa_numbers = recent_100['pa_number'].values
    rolling_xwoba_values = recent_100['rolling_xwoba'].values
    
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
                'formatted_date': recent_100.iloc[nearest_idx]['formatted_date'],
                'xwoba_display': recent_100.iloc[nearest_idx]['xwoba_display'],
                'xwoba_line': recent_100.iloc[nearest_idx]['xwoba_line'],
                'date_line': recent_100.iloc[nearest_idx]['date_line']
            })
        
        interpolated_df = pd.DataFrame(interpolated_data)
    else:
        # Fallback if not enough points
        interpolated_df = recent_100.copy()

    # Create a selection based on mouse x position
    mouse_selection = alt.selection_point(
        fields=['pa_number'],
        nearest=True,
        on='mouseover',
        empty='none',
        clear='mouseout'
    )

    # Create the main line chart
    line_chart = alt.Chart(recent_100).mark_line(
        size=3,
        color='#e53935',
        interpolate='monotone',
        clip=True
    ).encode(
        x=alt.X('pa_number:Q', 
                title=None,
                scale=alt.Scale(domain=[0, len(recent_100)-1]),
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
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
        tooltip=alt.value(None)
    ).add_params(mouse_selection)

    # Draw point on the line
    points = alt.Chart(interpolated_df).mark_point(
        size=100,
        filled=True,
        color='#e53935'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0)),
        tooltip=alt.value(None)
    ).transform_filter(mouse_selection)

    # Info box background - slightly taller to accommodate text better
    info_box = alt.Chart(interpolated_df).mark_rect(
        color='#f5f5f5',
        opacity=0.95,
        stroke='#999999',
        strokeWidth=1.5,
        cornerRadius=2
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(0.95), alt.value(0))
    ).transform_calculate(
        box_left='datum.pa_number - 8',    # Slightly wider
        box_right='datum.pa_number + 8',
        box_top='datum.rolling_xwoba - 0.012',     # Closer to dot
        box_bottom='datum.rolling_xwoba - 0.072'   # Taller box
    ).encode(
        x=alt.X('box_left:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
        x2=alt.X2('box_right:Q'),
        y=alt.Y('box_top:Q'),
        y2=alt.Y2('box_bottom:Q')
    ).transform_filter(mouse_selection)

    # First line of text - centered "xwOBA: .XXX"
    xwoba_text_line = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=27,      # Positioned in upper portion of box
        fontSize=11,
        fontWeight='normal',
        color='#333333'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
        y='rolling_xwoba:Q',
        text=alt.condition(mouse_selection, alt.Text('xwoba_line:N'), alt.value(' ')),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0))
    ).transform_filter(mouse_selection)

    # Second line of text - centered "Last PA: MMM DD"
    date_text_line = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=41,      # Positioned in lower portion of box
        fontSize=11,
        fontWeight='normal',
        color='#666666'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[0, len(recent_100)-1])),
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
        'x': [len(recent_100) - 1], 
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


def plot_ops_by_split(df, stat='OPS', title='OPS by Split'):
    """
    Create a horizontal bar chart for splits statistics
    
    Parameters:
    -----------
    df : DataFrame
        DataFrame with splits data
    stat : str
        The statistic to display (default: 'OPS')
    title : str
        Chart title
    
    Returns:
    --------
    alt.Chart
        Altair horizontal bar chart
    """
    
    # Calculate min and max for better color scaling
    stat_min = df[stat].min()
    stat_max = df[stat].max()
    stat_range = stat_max - stat_min
    
    # Set color domain based on actual data range with some padding
    color_min = max(0, stat_min - stat_range * 0.1)
    color_max = stat_max + stat_range * 0.1
    
    # Determine color based on stat value (green for good, red for bad)
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            # Y-axis for categories (horizontal bars)
            y=alt.Y('Split:N', 
                   sort='-x',  # Sort by the stat value
                   title=None,  # Remove axis title for cleaner look
                   axis=alt.Axis(
                       labelLimit=200,  # Allow longer labels
                       labelOverlap=False  # Force all labels to show
                   )),
            
            # X-axis for the statistic
            x=alt.X(f'{stat}:Q', 
                   title=stat,
                   scale=alt.Scale(domain=[0, stat_max * 1.1])),  # Add padding
            
            # Color bars based on performance (conditional coloring)
            color=alt.Color(f'{stat}:Q',
                          scale=alt.Scale(
                              scheme='redyellowgreen',
                              domain=[color_min, color_max],
                              clamp=True  # Clamp values to prevent black
                          ),
                          legend=None),  # Hide legend since color is intuitive
            
            # Enhanced tooltip
            tooltip=[
                alt.Tooltip('Split:N', title='Split'),
                alt.Tooltip('BA:Q', title='AVG', format='.3f'),
                alt.Tooltip('OBP:Q', title='OBP', format='.3f'),
                alt.Tooltip('SLG:Q', title='SLG', format='.3f'),
                alt.Tooltip('OPS:Q', title='OPS', format='.3f')
            ]
        )
        .properties(
            title={
                "text": title,
                "fontSize": 16,
                "fontWeight": "bold"
            },
            width=600,
            height=max(300, len(df) * 30)  # Dynamic height based on number of splits
        )
    )
    
    # Add value labels at the end of each bar for easy reading
    text = (
        alt.Chart(df)
        .mark_text(
            align='left',
            dx=5,  # Offset from bar end
            fontSize=11,
            fontWeight='bold',
            color='black'  # Force black color so it's always visible
        )
        .encode(
            y=alt.Y('Split:N', sort='-x'),
            x=alt.X(f'{stat}:Q'),
            text=alt.Text(f'{stat}:Q', format='.3f')
        )
    )
    
    return (chart + text).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelFontSize=11,
        titleFontSize=13
    )


def create_platoon_radar_chart(platoon_df):
    """
    Create a radar/spider chart comparing platoon splits (vs LHP and vs RHP)
    Uses cartesian coordinates (x, y) instead of polar (theta, radius)
    
    Parameters:
    -----------
    platoon_df : DataFrame
        DataFrame with platoon splits containing columns: Split, BA, OBP, SLG, OPS
    
    Returns:
    --------
    alt.Chart
        Altair radar chart
    """
    
    # Define the metrics to show
    metrics = ['BA', 'OBP', 'SLG', 'OPS']
    metric_labels = ['AVG', 'OBP', 'SLG', 'OPS']
    
    # Prepare data for radar chart
    radar_data = []
    
    for _, row in platoon_df.iterrows():
        split_name = row['Split']
        
        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            value = row[metric]
            
            # Normalize to 0-1 scale
            if metric == 'OPS':
                normalized = value / 2.0
            else:
                normalized = value
            
            # Calculate angle for this metric
            angle = (i / len(metrics)) * 2 * np.pi - np.pi / 2  # Start from top
            
            # Convert polar to cartesian
            x = normalized * np.cos(angle)
            y = normalized * np.sin(angle)
            
            radar_data.append({
                'metric': label,
                'value': normalized,
                'actual_value': value,
                'split': split_name,
                'x': x,
                'y': y,
                'order': i
            })
    
    radar_df = pd.DataFrame(radar_data)
    
    # Add closing point to complete the polygon
    closing_data = []
    for split in radar_df['split'].unique():
        first_point = radar_df[radar_df['split'] == split].iloc[0].copy()
        first_point['order'] = len(metrics)
        closing_data.append(first_point)
    
    radar_df = pd.concat([radar_df, pd.DataFrame(closing_data)], ignore_index=True)
    radar_df = radar_df.sort_values(['split', 'order'])
    
    # Create guide circles
    guide_data = []
    angles = np.linspace(0, 2 * np.pi, 100)
    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        for angle in angles:
            guide_data.append({
                'x': r * np.cos(angle),
                'y': r * np.sin(angle),
                'level': r
            })
    
    guides = alt.Chart(pd.DataFrame(guide_data)).mark_line(
        strokeDash=[2, 2],
        opacity=0.3,
        color='gray',
        strokeWidth=1
    ).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[-1.2, 1.2]), axis=None),
        y=alt.Y('y:Q', scale=alt.Scale(domain=[-1.2, 1.2]), axis=None),
        detail='level:N'
    )
    
    # Create axis lines from center
    axis_data = []
    for i, label in enumerate(metric_labels):
        angle = (i / len(metric_labels)) * 2 * np.pi - np.pi / 2
        axis_data.append({
            'x': 0,
            'y': 0,
            'x2': np.cos(angle),
            'y2': np.sin(angle),
            'metric': label
        })
    
    axes = alt.Chart(pd.DataFrame(axis_data)).mark_line(
        opacity=0.3,
        color='gray',
        strokeWidth=1
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        x2='x2:Q',
        y2='y2:Q'
    )
    
    # Data polygon (filled area)
    area = alt.Chart(radar_df).mark_line(
        opacity=0.2,
        interpolate='linear-closed',
        filled=True
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        color=alt.Color('split:N',
                       scale=alt.Scale(domain=['vs LHP', 'vs RHP'],
                                     range=['#FF6B6B', '#4ECDC4']),
                       legend=alt.Legend(title='Platoon Split')),
        order='order:O',
        detail='split:N'
    )
    
    # Data lines
    line = alt.Chart(radar_df).mark_line(
        strokeWidth=3,
        interpolate='linear-closed'
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        color=alt.Color('split:N',
                       scale=alt.Scale(domain=['vs LHP', 'vs RHP'],
                                     range=['#FF6B6B', '#4ECDC4'])),
        order='order:O',
        detail='split:N'
    )
    
    # Data points
    points = alt.Chart(radar_df[radar_df['order'] < len(metrics)]).mark_circle(
        size=100,
        opacity=1
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        color=alt.Color('split:N',
                       scale=alt.Scale(domain=['vs LHP', 'vs RHP'],
                                     range=['#FF6B6B', '#4ECDC4'])),
        tooltip=[
            alt.Tooltip('split:N', title='Split'),
            alt.Tooltip('metric:N', title='Metric'),
            alt.Tooltip('actual_value:Q', title='Value', format='.3f')
        ]
    )
    
    # Metric labels
    label_data = []
    for i, label in enumerate(metric_labels):
        angle = (i / len(metric_labels)) * 2 * np.pi - np.pi / 2
        label_data.append({
            'metric': label,
            'x': 1.15 * np.cos(angle),
            'y': 1.15 * np.sin(angle)
        })
    
    labels = alt.Chart(pd.DataFrame(label_data)).mark_text(
        fontSize=14,
        fontWeight='bold'
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        text='metric:N'
    )
    
    # Combine all layers
    chart = (guides + axes + area + line + points + labels).properties(
        width=500,
        height=500,
        title='Platoon Splits Comparison'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=False
    )
    
    return chart


def create_simple_platoon_radar(platoon_df):
    """
    Simplified radar chart for platoon splits
    
    Parameters:
    -----------
    platoon_df : DataFrame
        DataFrame with platoon splits containing columns: Split, BA, OBP, SLG, OPS
    
    Returns:
    --------
    alt.Chart
        Altair radar chart
    """
    metrics = ['BA', 'OBP', 'SLG', 'OPS']
    metric_labels = ['AVG', 'OBP', 'SLG', 'OPS']
    
    # Reshape data with cartesian coordinates
    data = []
    for _, row in platoon_df.iterrows():
        for i, (label, col) in enumerate(zip(metric_labels, metrics)):
            # Normalize OPS
            value = row[col] / 2.0 if col == 'OPS' else row[col]
            
            # Calculate angle
            angle = (i / len(metrics)) * 2 * np.pi - np.pi / 2
            
            # Convert to cartesian
            x = value * np.cos(angle)
            y = value * np.sin(angle)
            
            data.append({
                'Metric': label,
                'Value': value,
                'Split': row['Split'],
                'Display': f"{row[col]:.3f}",
                'x': x,
                'y': y,
                'order': i
            })
    
    chart_df = pd.DataFrame(data)
    
    # Add closing points
    closing_data = []
    for split in chart_df['Split'].unique():
        first_point = chart_df[chart_df['Split'] == split].iloc[0].copy()
        first_point['order'] = len(metrics)
        closing_data.append(first_point)
    
    chart_df = pd.concat([chart_df, pd.DataFrame(closing_data)], ignore_index=True)
    chart_df = chart_df.sort_values(['Split', 'order'])
    
    # Area
    area = alt.Chart(chart_df).mark_line(
        opacity=0.2,
        interpolate='linear-closed',
        filled=True
    ).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[-1.1, 1.1]), axis=None),
        y=alt.Y('y:Q', scale=alt.Scale(domain=[-1.1, 1.1]), axis=None),
        color=alt.Color('Split:N', scale=alt.Scale(scheme='set2')),
        order='order:O',
        detail='Split:N'
    )
    
    # Lines
    line = alt.Chart(chart_df).mark_line(
        strokeWidth=3,
        interpolate='linear-closed'
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        color=alt.Color('Split:N', scale=alt.Scale(scheme='set2')),
        order='order:O',
        detail='Split:N'
    )
    
    # Points
    points = alt.Chart(chart_df[chart_df['order'] < len(metrics)]).mark_circle(
        size=100
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        color=alt.Color('Split:N', 
                       scale=alt.Scale(scheme='set2'),
                       legend=alt.Legend(title='Platoon Split')),
        tooltip=['Split:N', 'Metric:N', 'Display:N']
    )
    
    # Labels
    label_data = []
    for i, label in enumerate(metric_labels):
        angle = (i / len(metric_labels)) * 2 * np.pi - np.pi / 2
        label_data.append({
            'metric': label,
            'x': 1.15 * np.cos(angle),
            'y': 1.15 * np.sin(angle)
        })
    
    labels = alt.Chart(pd.DataFrame(label_data)).mark_text(
        fontSize=12,
        fontWeight='bold'
    ).encode(
        x=alt.X('x:Q'),
        y=alt.Y('y:Q'),
        text='metric:N'
    )
    
    return (area + line + points + labels).properties(
        width=450,
        height=450,
        title='Platoon Splits'
    ).configure_view(
        strokeWidth=0
    )
