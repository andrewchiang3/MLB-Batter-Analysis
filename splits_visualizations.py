import altair as alt
import streamlit as st
import pandas as pd
import numpy as np

def display_best_ballpark(ballpark_df):
    """
    Minimalist clean design
    """
    best_park = ballpark_df.loc[ballpark_df['OPS'].idxmax()]
    park_code = best_park['Split']
    
    # Map ballpark codes to full names with cities
    ballpark_info = {
        'SEA': ('T-Mobile Park', 'Seattle'),
        'SF': ('Oracle Park', 'San Francisco'),
        'LAD': ('Dodger Stadium', 'Los Angeles'),
        'NYY': ('Yankee Stadium', 'New York'),
        'BOS': ('Fenway Park', 'Boston'),
        'CHC': ('Wrigley Field', 'Chicago'),
        'ATL': ('Truist Park', 'Atlanta'),
        'HOU': ('Minute Maid Park', 'Houston'),
        'TEX': ('Globe Life Field', 'Arlington'),
        'LAA': ('Angel Stadium', 'Anaheim'),
        'OAK': ('Oakland Coliseum', 'Oakland'),
        'SD': ('Petco Park', 'San Diego'),
        'ARI': ('Chase Field', 'Phoenix'),
        'COL': ('Coors Field', 'Denver'),
        'MIL': ('American Family Field', 'Milwaukee'),
        'MIN': ('Target Field', 'Minneapolis'),
        'CWS': ('Guaranteed Rate Field', 'Chicago'),
        'DET': ('Comerica Park', 'Detroit'),
        'CLE': ('Progressive Field', 'Cleveland'),
        'KC': ('Kauffman Stadium', 'Kansas City'),
        'STL': ('Busch Stadium', 'St. Louis'),
        'CIN': ('Great American Ball Park', 'Cincinnati'),
        'PIT': ('PNC Park', 'Pittsburgh'),
        'NYM': ('Citi Field', 'New York'),
        'PHI': ('Citizens Bank Park', 'Philadelphia'),
        'MIA': ('loanDepot park', 'Miami'),
        'WSH': ('Nationals Park', 'Washington'),
        'TB': ('Tropicana Field', 'St. Petersburg'),
        'BAL': ('Oriole Park', 'Baltimore'),
        'TOR': ('Rogers Centre', 'Toronto')
    }
    
    park_name, city = ballpark_info.get(park_code, (park_code, ''))
    
    st.markdown(f"""
        <div style='
            border-left: 4px solid #2ca02c;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
        '>
            <div style='font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;'>
                Top Performing Park
            </div>
            <div style='font-size: 28px; font-weight: bold; color: #1f77b4; margin-bottom: 5px;'>
                {park_name}
            </div>
            <div style='font-size: 14px; color: #888; margin-bottom: 15px;'>
                {city}
            </div>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <div style='font-size: 36px; font-weight: bold; color: #2ca02c;'>
                        {best_park['OPS']:.3f}
                    </div>
                    <div style='font-size: 12px; color: #666;'>
                        OPS
                    </div>
                </div>
                <div style='text-align: right; font-size: 13px; color: #666;'>
                    {int(best_park['G'])} Games<br/>
                    {int(best_park['HR'])} Home Runs<br/>
                    .{int(best_park['BA'] * 1000)} AVG
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)



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
                       legend=alt.Legend(title='Pitcher Handness')),
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
        title='Pitcher Handness Splits'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=False
    )
    
    return chart

def create_count_heatmap(count_df, stat='OPS', title='Performance by Count'):
    """
    Create a heatmap showing performance across different ball-strike counts
    This is the classic 4x3 grid (balls 0-3, strikes 0-2) that fans recognize
    
    Parameters:
    -----------
    count_df : DataFrame
        DataFrame with count splits data
    stat : str
        The statistic to display (default: 'OPS')
    title : str
        Chart title
    
    Returns:
    --------
    alt.Chart
        Altair heatmap chart
    """
    
    # Filter to just the individual count situations (0-0, 1-0, etc.)
    # Exclude aggregated counts like "After 1-0", "Batter Ahead", etc.
    count_pattern = count_df[count_df['Split'].str.match(r'^\d-\d Count$', na=False)].copy()
    
    # Parse balls and strikes from the Split column
    if len(count_pattern) > 0:
        count_pattern[['Balls', 'Strikes']] = count_pattern['Split'].str.extract(r'(\d)-(\d)')
        count_pattern['Balls'] = count_pattern['Balls'].astype(int)
        count_pattern['Strikes'] = count_pattern['Strikes'].astype(int)
    
    # Create complete grid of all possible count combinations
    all_counts = []
    for balls in range(4):  # 0-3 balls
        for strikes in range(3):  # 0-2 strikes
            all_counts.append({
                'Balls': balls,
                'Strikes': strikes,
                'Split': f'{balls}-{strikes} Count'
            })
    
    complete_grid = pd.DataFrame(all_counts)
    
    # Merge with actual data
    merged_data = complete_grid.merge(
        count_pattern,
        on=['Balls', 'Strikes', 'Split'],
        how='left'
    )
    
    # Create display label - show N/A for missing data
    merged_data['stat_label'] = merged_data[stat].apply(
        lambda x: 'N/A' if pd.isna(x) else f'{x:.3f}'
    )
    merged_data['has_data'] = merged_data[stat].notna()
    
    # Split into data with values and data without
    data_with_values = merged_data[merged_data['has_data']]
    data_without_values = merged_data[~merged_data['has_data']]
    
    # Calculate color scale based on actual data
    if len(data_with_values) > 0:
        stat_min = data_with_values[stat].min()
        stat_max = data_with_values[stat].max()
        stat_mid = data_with_values[stat].median()
    else:
        stat_min = 0.0
        stat_max = 1.0
        stat_mid = 0.5
    
    # Heatmap for cells WITH data
    heatmap_data = alt.Chart(data_with_values).mark_rect(
        stroke='black',
        strokeWidth=2
    ).encode(
        x=alt.X('Strikes:O', 
               title='Strikes',
               axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Balls:O', 
               title='Balls',
               sort='descending'),  # 0 balls at top, 3 at bottom
        color=alt.Color(f'{stat}:Q',
                       scale=alt.Scale(
                           scheme='redyellowgreen',
                           domain=[stat_min, stat_max]
                       ),
                       legend=alt.Legend(title=stat)),
        tooltip=[
            alt.Tooltip('Split:N', title='Count'),
            alt.Tooltip('PA:Q', title='PA'),
            alt.Tooltip('BA:Q', title='AVG', format='.3f'),
            alt.Tooltip('OBP:Q', title='OBP', format='.3f'),
            alt.Tooltip('SLG:Q', title='SLG', format='.3f'),
            alt.Tooltip('OPS:Q', title='OPS', format='.3f')
        ]
    )
    
    # Heatmap for cells WITHOUT data (gray)
    heatmap_no_data = alt.Chart(data_without_values).mark_rect(
        stroke='black',
        strokeWidth=2,
        fill='#e0e0e0'
    ).encode(
        x=alt.X('Strikes:O', title='Strikes'),
        y=alt.Y('Balls:O', sort='descending'),
        tooltip=[
            alt.Tooltip('Split:N', title='Count'),
            alt.Tooltip('stat_label:N', title=stat)
        ]
    )
    
    # Combine heatmap layers
    heatmap = heatmap_no_data + heatmap_data
    
    # Text labels for cells WITH data
    text_data = alt.Chart(data_with_values).mark_text(
        fontSize=14,
        fontWeight='bold'
    ).encode(
        x=alt.X('Strikes:O'),
        y=alt.Y('Balls:O', sort='descending'),
        text=alt.Text(f'{stat}:Q', format='.3f'),
        color=alt.condition(
            f'datum.{stat} > {stat_mid}',  # White text for higher values
            alt.value('white'),
            alt.value('black')
        )
    )
    
    # Text labels for cells WITHOUT data (N/A)
    text_no_data = alt.Chart(data_without_values).mark_text(
        fontSize=14,
        fontWeight='bold',
        color='#666666'
    ).encode(
        x=alt.X('Strikes:O'),
        y=alt.Y('Balls:O', sort='descending'),
        text='stat_label:N'
    )
    
    # Combine text layers
    text = text_data + text_no_data
    
    return (heatmap + text).properties(
        width=400,
        height=500,
        title={
            "text": title,
            "fontSize": 16,
            "fontWeight": "bold"
        }
    ).configure_view(
        strokeWidth=0
    )