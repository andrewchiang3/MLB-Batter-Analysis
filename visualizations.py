import altair as alt
import pandas as pd
import numpy as np
import streamlit as st
from scipy import interpolate
from pybaseball import spraychart
from utils import categorize_count

# Constants
LEAGUE_AVG_XWOBA = 0.324
LEAGUE_AVG_CHASE_RATE = 28.0
DEFAULT_MAX_ROLLING = 100
MIN_ROLLING_PERIODS_RATIO = 0.2
MIN_ROLLING_PERIODS_ABSOLUTE = 10
INTERPOLATION_DENSITY = 20  # 20x more points for smooth tracking


def prepare_xwoba_data(data: pd.DataFrame, max_rolling: int = DEFAULT_MAX_ROLLING) -> pd.DataFrame:
    """
    Prepare and calculate rolling xwOBA data for visualization.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Statcast batting data for a specified date and player
    max_rolling : int
        Maximum rolling window size (default 100, adjusts if fewer PAs available)
    
    Returns:
    --------
    pd.DataFrame : Prepared data with rolling xwOBA calculations
    """
    # Filter to valid plate appearances
    valid_pa = data[data['woba_denom'] == 1].copy()
    valid_pa['game_date'] = pd.to_datetime(valid_pa['game_date'])
    valid_pa = valid_pa.sort_values('game_date').reset_index(drop=True)

    # Use estimated_woba_using_speedangle when available, otherwise fall back to woba_value
    valid_pa['xwoba_value'] = valid_pa['estimated_woba_using_speedangle'].fillna(valid_pa['woba_value'])

    # Determine actual rolling window based on available data
    total_pas = len(valid_pa)
    actual_rolling = min(max_rolling, total_pas)
    min_periods = max(MIN_ROLLING_PERIODS_ABSOLUTE, int(actual_rolling * MIN_ROLLING_PERIODS_RATIO))
    
    # Calculate rolling average on the full dataset
    valid_pa['rolling_xwoba'] = valid_pa['xwoba_value'].rolling(
        window=actual_rolling, 
        min_periods=min_periods
    ).mean()

    # Get the most recent PAs
    num_recent = min(actual_rolling, total_pas)
    recent_pas = valid_pa.tail(num_recent).copy()
    recent_pas = recent_pas.reset_index(drop=True)
    recent_pas['pa_number'] = range(len(recent_pas))
    
    return recent_pas


def format_date_with_ordinal(date: pd.Timestamp) -> str:
    """
    Format date with ordinal suffix (e.g., 'Jan 1st', 'Feb 2nd').
    
    Parameters:
    -----------
    date : pd.Timestamp
        Date to format
    
    Returns:
    --------
    str : Formatted date string
    """
    day = date.day
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return date.strftime(f'%b {day}{suffix}')


def create_interpolated_data(recent_pas: pd.DataFrame) -> pd.DataFrame:
    """
    Create densely interpolated data for ultra-smooth tracking.
    
    Parameters:
    -----------
    recent_pas : pd.DataFrame
        Recent plate appearances data with rolling xwOBA
    
    Returns:
    --------
    pd.DataFrame : Interpolated data for smooth visualization
    """
    pa_numbers = recent_pas['pa_number'].values
    rolling_xwoba_values = recent_pas['rolling_xwoba'].values
    
    # Remove any NaN values for interpolation
    valid_mask = ~np.isnan(rolling_xwoba_values)
    pa_numbers_clean = pa_numbers[valid_mask]
    rolling_xwoba_clean = rolling_xwoba_values[valid_mask]
    
    # Need at least 4 points for cubic spline
    if len(pa_numbers_clean) <= 3:
        return recent_pas.copy()
    
    # Create cubic spline interpolation for smooth curve
    cs = interpolate.CubicSpline(pa_numbers_clean, rolling_xwoba_clean)
    
    # Create very dense points for ultra-smooth tracking
    dense_pa = np.linspace(
        pa_numbers_clean[0], 
        pa_numbers_clean[-1], 
        len(pa_numbers_clean) * INTERPOLATION_DENSITY
    )
    dense_xwoba = cs(dense_pa)
    
    # Create interpolated dataframe
    interpolated_data = []
    for pa, xwoba_val in zip(dense_pa, dense_xwoba):
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
    
    return pd.DataFrame(interpolated_data)


def create_line_chart(recent_pas: pd.DataFrame, x_min: float, x_max: float) -> alt.Chart:
    """
    Create the main xwOBA line chart.
    
    Parameters:
    -----------
    recent_pas : pd.DataFrame
        Recent plate appearances data
    x_min : float
        Minimum x-axis value
    x_max : float
        Maximum x-axis value
    
    Returns:
    --------
    alt.Chart : Line chart layer
    """
    return alt.Chart(recent_pas).mark_line(
        size=3,
        color='#e53935',
        interpolate='monotone',
        clip=True
    ).encode(
        x=alt.X('pa_number:Q', 
                title=None,
                scale=alt.Scale(domain=[x_min, x_max]),
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


def create_selector_and_points(interpolated_df: pd.DataFrame, 
                               x_min: float,
                               x_max: float) -> tuple:
    """
    Create the mouse selection rule and tracking points.
    
    Parameters:
    -----------
    interpolated_df : pd.DataFrame
        Interpolated data
    x_min : float
        Minimum x-axis value
    x_max : float
        Maximum x-axis value
    
    Returns:
    --------
    tuple : (selector_rules, mouse_selection, points)
    """
    # Create mouse selection
    mouse_selection = alt.selection_point(
        fields=['pa_number'],
        nearest=True,
        on='mouseover',
        empty='none',
        clear='mouseout'
    )

    # Transparent rule for selection
    selector_rules = alt.Chart(interpolated_df).mark_rule(
        opacity=0,
        size=2
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[x_min, x_max])),
        tooltip=alt.value(None)
    ).add_params(mouse_selection)

    # Points on the line
    points = alt.Chart(interpolated_df).mark_point(
        size=100,
        filled=True,
        color='#e53935'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[x_min, x_max])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0)),
        tooltip=alt.value(None)
    ).transform_filter(mouse_selection)

    return selector_rules, mouse_selection, points


def create_info_box(interpolated_df: pd.DataFrame, 
                    mouse_selection,
                    x_min: float,
                    x_max: float) -> tuple:
    """
    Create the info box with xwOBA and date information.
    
    Parameters:
    -----------
    interpolated_df : pd.DataFrame
        Interpolated data
    mouse_selection
        Mouse selection parameter from Altair
    x_min : float
        Minimum x-axis value
    x_max : float
        Maximum x-axis value
    
    Returns:
    --------
    tuple : (info_box_bg, xwoba_text, date_text)
    """
    # Calculate dynamic box width based on x-axis range
    x_range = x_max - x_min
    # Scale box width: smaller for narrow ranges, larger for wide ranges
    # Use a base size and scale it proportionally
    box_half_width = max(3, min(8, x_range * 0.08))
    
    # Info box background with fixed vertical size but dynamic horizontal size
    info_box = alt.Chart(interpolated_df).mark_rect(
        color='#f5f5f5',
        opacity=0.95,
        stroke='#999999',
        strokeWidth=1.5,
        cornerRadius=2
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[x_min, x_max])),
        y=alt.Y('rolling_xwoba:Q'),
        opacity=alt.condition(mouse_selection, alt.value(0.95), alt.value(0))
    ).transform_calculate(
        box_left=f'datum.pa_number - {box_half_width}',
        box_right=f'datum.pa_number + {box_half_width}',
        box_top='datum.rolling_xwoba - 0.012',
        box_bottom='datum.rolling_xwoba - 0.072'
    ).encode(
        x=alt.X('box_left:Q', scale=alt.Scale(domain=[x_min, x_max])),
        x2=alt.X2('box_right:Q'),
        y=alt.Y('box_top:Q'),
        y2=alt.Y2('box_bottom:Q')
    ).transform_filter(mouse_selection)

    # xwOBA text line
    xwoba_text = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=27,
        fontSize=11,
        fontWeight='normal',
        color='#333333'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[x_min, x_max])),
        y='rolling_xwoba:Q',
        text=alt.condition(mouse_selection, alt.Text('xwoba_line:N'), alt.value(' ')),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0))
    ).transform_filter(mouse_selection)

    # Date text line
    date_text = alt.Chart(interpolated_df).mark_text(
        align='center',
        dx=0,
        dy=41,
        fontSize=11,
        fontWeight='normal',
        color='#666666'
    ).encode(
        x=alt.X('pa_number:Q', scale=alt.Scale(domain=[x_min, x_max])),
        y='rolling_xwoba:Q',
        text=alt.condition(mouse_selection, 'date_line:N', alt.value(' ')),
        opacity=alt.condition(mouse_selection, alt.value(1), alt.value(0))
    ).transform_filter(mouse_selection)

    return info_box, xwoba_text, date_text


def create_league_average_line(x_max: float) -> tuple:
    """
    Create the league average reference line and label.
    
    Parameters:
    -----------
    x_max : float
        Maximum x-axis value for positioning label
    
    Returns:
    --------
    tuple : (league_avg_line, league_avg_text)
    """
    league_avg_line = alt.Chart(pd.DataFrame({'y': [LEAGUE_AVG_XWOBA]})).mark_rule(
        strokeDash=[3, 3],
        color='#999999',
        size=1.5,
        opacity=0.8
    ).encode(
        y='y:Q'
    )

    league_avg_text = alt.Chart(pd.DataFrame({
        'x': [x_max], 
        'y': [LEAGUE_AVG_XWOBA - 0.012], 
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

    return league_avg_line, league_avg_text


def xwOBA_graph(data: pd.DataFrame, max_rolling: int = DEFAULT_MAX_ROLLING) -> alt.Chart:
    """
    Create a line chart showing rolling xwOBA over plate appearances.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Statcast batting data for a specified date and player
    max_rolling : int
        Maximum rolling window size (default 100, adjusts if fewer PAs available)
    
    Returns:
    --------
    alt.Chart : Complete xwOBA visualization with interactive tracking
    """
    # Prepare data
    recent_pas = prepare_xwoba_data(data, max_rolling)
    
    # Format dates and create display values
    recent_pas['formatted_date'] = recent_pas['game_date'].apply(format_date_with_ordinal)
    recent_pas['xwoba_display'] = recent_pas['rolling_xwoba'].apply(
        lambda x: f'.{int(x * 1000):03d}' if pd.notna(x) else ''
    )
    recent_pas['xwoba_line'] = 'xwOBA: ' + recent_pas['xwoba_display']
    recent_pas['date_line'] = 'Last PA: ' + recent_pas['formatted_date']
    
    # Create interpolated data for smooth tracking
    interpolated_df = create_interpolated_data(recent_pas)
    
    # Calculate x-axis domain based on actual data range with small padding
    x_min = recent_pas['pa_number'].min()
    x_max = recent_pas['pa_number'].max()
    
    # Add small padding (5% on each side) to prevent line from touching edges
    x_range = x_max - x_min
    if x_range > 0:
        padding = x_range * 0.05
        x_min = max(0, x_min - padding)
        x_max = x_max + padding
    else:
        # Handle edge case where there's only one data point
        x_min = max(0, x_min - 1)
        x_max = x_max + 1
    
    # Create chart layers
    line_chart = create_line_chart(recent_pas, x_min, x_max)
    selector_rules, mouse_selection, points = create_selector_and_points(
        interpolated_df, x_min, x_max
    )
    info_box, xwoba_text, date_text = create_info_box(
        interpolated_df, mouse_selection, x_min, x_max
    )
    league_avg_line, league_avg_text = create_league_average_line(x_max)
    
    # Combine all layers
    chart = (
        line_chart + selector_rules + points + info_box + 
        xwoba_text + date_text + league_avg_line + league_avg_text
    ).properties(
        width=700,
        height=400
    ).configure_view(
        strokeWidth=0,
        fill='white'
    ).configure_axis(
        titleFontSize=0
    )

    return chart


def spray_chart(data: pd.DataFrame):
    """
    Render spray chart for all hits.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Statcast batting data
    
    Returns:
    --------
    matplotlib.figure.Figure : Spray chart figure
    """
    hits = ['single', 'double', 'triple', 'home_run']
    data_filtered = data[data['events'].isin(hits)]

    ax = spraychart(data_filtered, 'yankees', title='Hits Spray chart')
    return ax.get_figure()


def calculate_chase_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate chase rate and zone swing metrics.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Player statcast data
    
    Returns:
    --------
    dict : Dictionary with chase_rate, zone_swing_rate, and situational data
    """
    player_data = df.copy()
    player_data['in_zone'] = player_data['zone'].apply(
        lambda x: x <= 9 if pd.notna(x) else None
    )

    # Identify swings
    swing_descriptions = [
        'swinging_strike', 'swinging_strike_blocked', 'foul', 'foul_tip', 
        'hit_into_play', 'hit_into_play_score', 'hit_into_play_no_out',
        'foul_bunt', 'missed_bunt', 'swinging_pitchout'
    ]
    player_data['swung'] = player_data['description'].isin(swing_descriptions)
    
    # Create count categories
    player_data['count_situation'] = player_data.apply(categorize_count, axis=1)

    # Calculate overall rates
    total_pitches_out = len(player_data[player_data['in_zone'] == False])
    swings_out = len(player_data[(player_data['in_zone'] == False) & (player_data['swung'] == True)])
    total_pitches_in = len(player_data[player_data['in_zone'] == True])
    swings_in = len(player_data[(player_data['in_zone'] == True) & (player_data['swung'] == True)])
    
    chase_rate = (swings_out / total_pitches_out * 100) if total_pitches_out > 0 else 0
    zone_swing_rate = (swings_in / total_pitches_in * 100) if total_pitches_in > 0 else 0

    # Calculate by situation
    situations = ['Hitter ahead', 'Pitcher ahead', '2-strike (pressure)']
    chase_by_situation = []
    
    for situation in situations:
        situation_data = player_data[player_data['count_situation'] == situation]
        out_zone = situation_data[situation_data['in_zone'] == False]
        chase_swings = len(out_zone[out_zone['swung'] == True])
        total_out = len(out_zone)
        
        rate = (chase_swings / total_out * 100) if total_out > 0 else 0
        
        chase_by_situation.append({
            'Situation': situation,
            'Chase Rate': rate,
            'Label': f"{situation}\n({chase_swings}/{total_out})",
            'Count': f"({chase_swings}/{total_out})"
        })
    
    return {
        'chase_rate': chase_rate,
        'zone_swing_rate': zone_swing_rate,
        'chase_by_situation': pd.DataFrame(chase_by_situation)
    }


def create_chase_rate_chart(chase_df: pd.DataFrame, player_name: str) -> alt.Chart:
    """
    Create a bar chart for chase rate by count situation.
    
    Parameters:
    -----------
    chase_df : pd.DataFrame
        DataFrame with chase rate by situation
    player_name : str
        Player name for title
    
    Returns:
    --------
    alt.Chart : Chase rate bar chart
    """
    # Define colors for each situation
    color_scale = alt.Scale(
        domain=['Hitter ahead', 'Pitcher ahead', '2-strike (pressure)'],
        range=['green', 'orange', 'red']
    )
    
    # Calculate max for y-axis scaling
    max_rate = chase_df['Chase Rate'].max() if len(chase_df) > 0 else 50
    
    # Create bars
    bars = alt.Chart(chase_df).mark_bar(
        opacity=0.7,
        stroke='black',
        strokeWidth=2
    ).encode(
        x=alt.X('Label:N', title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Chase Rate:Q', 
                title='Chase Rate (%)', 
                scale=alt.Scale(domain=[0, max_rate * 1.2])),
        color=alt.Color('Situation:N', scale=color_scale, legend=None)
    )
    
    # Add value labels
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
    rule = alt.Chart(pd.DataFrame({'y': [LEAGUE_AVG_CHASE_RATE]})).mark_rule(
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
        text=f'MLB Average (~{LEAGUE_AVG_CHASE_RATE:.0f}%)',
        fontSize=11,
        color='blue'
    )
    
    # Combine layers
    chart = (bars + text + rule + rule_label).properties(
        width=600,
        height=400,
        title=f'{player_name} - Chase Rate by Count Situation'
    ).configure_axis(
        grid=True,
        gridOpacity=0.3
    ).configure_title(
        fontSize=14,
        fontWeight='bold',
        anchor='start'
    )
    
    return chart


def chase_rate(df: pd.DataFrame):
    """
    Calculate and display chase rate analysis with metrics and chart.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Player statcast data
    """
    # Calculate metrics
    metrics = calculate_chase_metrics(df)
    
    # Display overall discipline metrics
    st.write("### Overall Discipline Metrics")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Chase Rate", 
            f"{metrics['chase_rate']:.1f}%", 
            help="How often batter swings at pitches outside the zone"
        )
    
    with col2:
        st.metric(
            "Zone Swing Rate", 
            f"{metrics['zone_swing_rate']:.1f}%",
            help="How often batter swings at pitches in the zone"
        )
    
    with col3:
        delta = metrics['chase_rate'] - LEAGUE_AVG_CHASE_RATE
        st.metric(
            f"vs MLB Avg (~{LEAGUE_AVG_CHASE_RATE:.0f}%)", 
            f"{delta:+.1f}%",
            delta=f"{delta:.1f}%",
            delta_color="inverse"
        )
    
    # Display chase rate by count situation
    st.write("### Chase Rate by Count Situation")
    
    chart = create_chase_rate_chart(
        metrics['chase_by_situation'], 
        st.session_state.get('player_name', 'Player')
    )
    st.altair_chart(chart, use_container_width=True)


def heat_map(df: pd.DataFrame):
    """
    Create a heatmap showing batting average by strike zone location.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Zone batting average data with plate_x, plate_z, and batting average
    """
    # Detect batting average column name
    possible_cols = ['batting_avg', 'avg', 'batting_average', 'BA']
    avg_col = next((col for col in possible_cols if col in df.columns), None)

    if avg_col is None:
        st.error(f"No batting average column found. Columns: {list(df.columns)}")
        return

    df = df.copy()

    # Define explicit category orders for proper zone grid mapping
    x_order = ['Left', 'Middle', 'Right']
    y_order = ['High', 'Mid', 'Low']

    # Create a complete grid with all 9 zones
    all_zones = pd.DataFrame([
        {'plate_x': x, 'plate_z': z}
        for z in y_order
        for x in x_order
    ])
    
    # Merge with actual data to fill in missing zones
    df_complete = all_zones.merge(df, on=['plate_x', 'plate_z'], how='left')
    
    # Create display labels - show N/A for missing data
    df_complete['batting_avg_label'] = df_complete[avg_col].apply(
        lambda x: 'N/A' if pd.isna(x) else f'{x:.3f}'
    )
    
    # For zones with data, also create numeric labels for tooltips
    df_complete['has_data'] = df_complete[avg_col].notna()

    # Calculate dynamic color scale based on actual data (excluding NaN)
    valid_data = df_complete[df_complete['has_data']]
    if len(valid_data) > 0:
        min_avg = valid_data[avg_col].min()
        max_avg = valid_data[avg_col].max()
        mid_avg = valid_data[avg_col].median()
    else:
        # Defaults if no data at all
        min_avg = 0.0
        max_avg = 1.0
        mid_avg = 0.5
    
    # Split data into zones with data and zones without
    zones_with_data = df_complete[df_complete['has_data']]
    zones_no_data = df_complete[~df_complete['has_data']]
    
    # Create heatmap for zones WITH data (red-blue color scheme)
    heatmap_data = alt.Chart(zones_with_data).mark_rect(stroke='black', strokeWidth=2).encode(
        x=alt.X('plate_x:O',
                sort=x_order,
                title='Horizontal Distance (Catcher Perspective) [ft]',
                axis=alt.Axis(labelFontSize=14, titleFontSize=14, titleFontWeight='bold')),
        y=alt.Y('plate_z:O',
                sort=y_order,
                title='Vertical Distance (Above Home Plate) [ft]',
                axis=alt.Axis(labelFontSize=14, titleFontSize=14, titleFontWeight='bold')),
        color=alt.Color(
            f'{avg_col}:Q',
            title='Batting Average',
            scale=alt.Scale(
                scheme='redblue',
                domain=[min_avg, max_avg],
                domainMid=mid_avg,
                reverse=True,  # Red for high, blue for low
                clamp=True
            ),
            legend=alt.Legend(titleFontSize=13, labelFontSize=12, titleFontWeight='bold')
        ),
        tooltip=[
            alt.Tooltip('plate_x:O', title='X Zone'),
            alt.Tooltip('plate_z:O', title='Z Zone'),
            alt.Tooltip('batting_avg_label:N', title='Batting Average')
        ]
    )
    
    # Create heatmap for zones WITHOUT data (gray)
    heatmap_no_data = alt.Chart(zones_no_data).mark_rect(
        stroke='black', 
        strokeWidth=2,
        fill='#e0e0e0'
    ).encode(
        x=alt.X('plate_x:O', sort=x_order),
        y=alt.Y('plate_z:O', sort=y_order),
        tooltip=[
            alt.Tooltip('plate_x:O', title='X Zone'),
            alt.Tooltip('plate_z:O', title='Z Zone'),
            alt.Tooltip('batting_avg_label:N', title='Batting Average')
        ]
    )
    
    # Combine both heatmap layers
    heatmap = heatmap_no_data + heatmap_data

    # Add text labels for zones with data (white or black based on background)
    text_data = alt.Chart(zones_with_data).mark_text(
        align='center',
        baseline='middle',
        fontSize=18,
        fontWeight='bold'
    ).encode(
        x=alt.X('plate_x:O', sort=x_order),
        y=alt.Y('plate_z:O', sort=y_order),
        text='batting_avg_label:N',
        color=alt.condition(
            f'datum.{avg_col} > {mid_avg}',
            alt.value('white'),
            alt.value('black')
        )
    )
    
    # Add text labels for zones without data (gray text for N/A)
    text_no_data = alt.Chart(zones_no_data).mark_text(
        align='center',
        baseline='middle',
        fontSize=18,
        fontWeight='bold',
        color='#666666'
    ).encode(
        x=alt.X('plate_x:O', sort=x_order),
        y=alt.Y('plate_z:O', sort=y_order),
        text='batting_avg_label:N'
    )
    
    # Combine text layers
    text = text_data + text_no_data

    # Combine and configure
    chart = (heatmap + text).properties(
        width=450,
        height=600,
        title={
            'text': f"{st.session_state.get('player_name', 'Player')} - Batting Average by Zone",
            'fontSize': 18,
            'fontWeight': 'bold',
            'anchor': 'middle'
        }
    ).configure_view(
        stroke='black',
        strokeWidth=2,
        fill='#f9f9fa'
    )

    st.altair_chart(chart, use_container_width=False)