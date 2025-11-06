import altair as alt
import pandas as pd
import numpy as np
from scipy import interpolate
from pybaseball import spraychart

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