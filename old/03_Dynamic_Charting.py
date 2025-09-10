# # page 03
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from utils import load_data_from_mongo

# st.set_page_config(layout="wide")
# st.title("📊 Dynamic Charting Tool")

# # --- 1. Load Data ---
# # This uses the same cached function, so it's very fast
# df_raw = load_data_from_mongo("telemetry_data_clean", "SmartFarm")
# df_smartfarm = df_raw[df_raw['deviceName'] == 'SmartFarm'].copy()

# # --- 2. Create Interactive Widgets for User Selection ---
# st.subheader("Chart Controls")

# # Get a list of all numeric columns for the user to choose from
# numeric_columns = df_smartfarm.select_dtypes(include=['number']).columns.tolist()

# # Use columns for a cleaner layout
# col1, col2, col3 = st.columns(3)

# with col1:
#     # Dropdown for Chart Type
#     chart_type = st.selectbox("Select Chart Type", ["Line Chart", "Bar Chart", "Histogram"])
# with col2:
#     # Dropdown for Y-Axis
#     y_axis_variable = st.selectbox("Select Y-Axis Variable", options=numeric_columns, index=numeric_columns.index('temperature'))
# with col3:
#     # Dropdown for Color Grouping (Optional)
#     # Let's add deviceName here for future use if you have more devices
#     color_variable = st.selectbox("Group by Color (Optional)", options=[None] + ['deviceName'])

# # --- 3. Generate and Display the Chart Dynamically ---
# st.divider()

# if df_smartfarm.empty:
#     st.warning("No data available to plot.")
# else:
#     st.subheader(f"{chart_type} of {y_axis_variable}")

#     # --- Line Chart Logic ---
#     if chart_type == "Line Chart":
#         fig = px.line(df_smartfarm,
#                       x='timestamp_local_dt',
#                       y=y_axis_variable,
#                       color=color_variable,
#                       title=f"Time series of {y_axis_variable}")
#         st.plotly_chart(fig, use_container_width=True)

#     # --- Bar Chart Logic ---
#     elif chart_type == "Bar Chart":
#         # Bar charts are better for aggregated data, here we'll just plot it against time
#         fig = px.bar(df_smartfarm,
#                      x='timestamp_local_dt',
#                      y=y_axis_variable,
#                      color=color_variable,
#                      title=f"Bar chart of {y_axis_variable}")
#         st.plotly_chart(fig, use_container_width=True)

#     # --- Histogram Logic ---
#     elif chart_type == "Histogram":
#         # Histograms show the distribution of a single variable, x-axis is not time
#         fig = px.histogram(df_smartfarm,
#                            x=y_axis_variable,
#                            color=color_variable,
#                            title=f"Distribution of {y_axis_variable}",
#                            marginal="box") # Add a box plot for more detail
#         st.plotly_chart(fig, use_container_width=True)

# pages/03_Dynamic_Charting.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import load_data_from_mongo, calculate_vpd
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(layout="wide", page_title="Dynamic Charting")
st.title("📊 Advanced Dynamic Charting Tool")

# --- 1. Initialize Session State ---
if 'chart_configs' not in st.session_state:
    st.session_state.chart_configs = []
if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

# --- 2. Load Data ---
@st.cache_data(ttl=300)
def load_all_data():
    """โหลดข้อมูลจากทั้ง SmartFarm และ Raspberry Pi"""
    df_smartfarm = load_data_from_mongo("telemetry_data_clean", "SmartFarm", time_delta_days=7)
    df_rpi = load_data_from_mongo("raspberry_pi_telemetry_clean", "raspberry_pi_status", time_delta_days=7)
    
    # Add VPD to SmartFarm data
    if not df_smartfarm.empty:
        df_smartfarm['vpd'] = df_smartfarm.apply(
            lambda row: calculate_vpd(row['temperature'], row['humidity']), 
            axis=1
        )
        df_smartfarm['data_source'] = 'SmartFarm'
    
    if not df_rpi.empty:
        df_rpi['data_source'] = 'Raspberry Pi'
    
    return df_smartfarm, df_rpi

df_smartfarm, df_rpi = load_all_data()

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.header("🎨 Chart Builder")
    
    # Data Source Selection
    data_source = st.selectbox(
        "📁 Select Data Source:",
        ["SmartFarm", "Raspberry Pi", "Both (Comparison)"]
    )
    
    # Select the appropriate dataframe
    if data_source == "SmartFarm":
        df = df_smartfarm
    elif data_source == "Raspberry Pi":
        df = df_rpi
    else:  # Both
        st.session_state.comparison_mode = True
        df = pd.concat([df_smartfarm, df_rpi], ignore_index=True)
    
    if df.empty:
        st.error("No data available for selected source")
        st.stop()
    
    # Get numeric columns
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    
    st.divider()
    
    # Chart Type Selection with Icons
    chart_types = {
        "Line Chart": "📈",
        "Area Chart": "🏔️",
        "Bar Chart": "📊",
        "Scatter Plot": "🎯",
        "Box Plot": "📦",
        "Histogram": "📊",
        "Heatmap": "🔥",
        "3D Scatter": "🌐",
        "Violin Plot": "🎻",
        "Sunburst": "☀️"
    }
    
    chart_type = st.selectbox(
        "📊 Chart Type:",
        list(chart_types.keys()),
        format_func=lambda x: f"{chart_types[x]} {x}"
    )
    
    st.divider()
    
    # Variable Selection based on chart type
    st.subheader("📐 Axis Configuration")
    
    if chart_type in ["Line Chart", "Area Chart", "Bar Chart", "Scatter Plot"]:
        # X-axis selection
        x_axis = st.selectbox(
            "X-Axis:",
            ['timestamp_local_dt'] + numeric_columns,
            index=0
        )
        
        # Y-axis selection (allow multiple for some charts)
        if chart_type in ["Line Chart", "Area Chart"]:
            y_axes = st.multiselect(
                "Y-Axis (multiple allowed):",
                numeric_columns,
                default=[numeric_columns[0]] if numeric_columns else []
            )
        else:
            y_axes = [st.selectbox("Y-Axis:", numeric_columns)]
        
        # Color grouping
        categorical_cols = ['deviceName', 'data_source'] if 'data_source' in df.columns else ['deviceName']
        color_by = st.selectbox(
            "Color By (optional):",
            [None] + categorical_cols + numeric_columns
        )
        
        # Size for scatter plots
        if chart_type == "Scatter Plot":
            size_by = st.selectbox(
                "Size By (optional):",
                [None] + numeric_columns
            )
        else:
            size_by = None
    
    elif chart_type in ["Histogram", "Box Plot", "Violin Plot"]:
        y_axes = st.multiselect(
            "Variables to analyze:",
            numeric_columns,
            default=[numeric_columns[0]] if numeric_columns else []
        )
        x_axis = None
        color_by = st.selectbox(
            "Group By (optional):",
            [None] + ['deviceName', 'data_source'] if 'data_source' in df.columns else [None] + ['deviceName']
        )
        size_by = None
    
    elif chart_type == "Heatmap":
        st.info("Heatmap will show correlations between all numeric variables")
        x_axis = None
        y_axes = numeric_columns
        color_by = None
        size_by = None
    
    elif chart_type == "3D Scatter":
        x_axis = st.selectbox("X-Axis:", numeric_columns, index=0)
        y_axis = st.selectbox("Y-Axis:", numeric_columns, index=1 if len(numeric_columns) > 1 else 0)
        z_axis = st.selectbox("Z-Axis:", numeric_columns, index=2 if len(numeric_columns) > 2 else 0)
        y_axes = [y_axis, z_axis]
        color_by = st.selectbox(
            "Color By:",
            [None] + numeric_columns + ['deviceName']
        )
        size_by = None
    
    else:  # Sunburst
        st.info("Sunburst chart for hierarchical data")
        # Special handling for sunburst
        x_axis = None
        y_axes = []
        color_by = None
        size_by = None
    
    st.divider()
    
    # Advanced Options
    with st.expander("⚙️ Advanced Options"):
        # Aggregation for time series
        if x_axis == 'timestamp_local_dt' and chart_type in ["Line Chart", "Bar Chart", "Area Chart"]:
            aggregation = st.selectbox(
                "Time Aggregation:",
                ["None", "1min", "5min", "15min", "30min", "1H", "1D"]
            )
            
            agg_function = st.selectbox(
                "Aggregation Function:",
                ["mean", "sum", "max", "min", "median", "std"]
            )
        else:
            aggregation = "None"
            agg_function = "mean"
        
        # Chart height
        chart_height = st.slider("Chart Height (px):", 400, 1000, 600, 50)
        
        # Theme
        theme = st.selectbox(
            "Theme:",
            ["plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white"]
        )
        
        # Show data table
        show_table = st.checkbox("Show Data Table", value=False)
        
        # Enable animation for time series
        if x_axis == 'timestamp_local_dt':
            animate = st.checkbox("Enable Animation", value=False)
        else:
            animate = False

# --- 4. Main Content Area ---

# Apply time aggregation if needed
if aggregation != "None" and x_axis == 'timestamp_local_dt':
    df_plot = df.copy()
    df_plot = df_plot.set_index('timestamp_local_dt')
    
    # Group by additional columns if color_by is set
    if color_by and color_by in ['deviceName', 'data_source']:
        df_plot = df_plot.groupby(color_by).resample(aggregation).agg(agg_function).reset_index()
    else:
        df_plot = df_plot.resample(aggregation).agg(agg_function).reset_index()
    
    st.info(f"📊 Data aggregated by {aggregation} using {agg_function}")
else:
    df_plot = df.copy()

# Create the chart based on type
if chart_type == "Line Chart" and y_axes:
    if len(y_axes) == 1:
        fig = px.line(
            df_plot,
            x=x_axis,
            y=y_axes[0],
            color=color_by,
            title=f"{y_axes[0]} over {x_axis}",
            template=theme
        )
    else:
        # Multiple Y-axes
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        colors = px.colors.qualitative.Plotly
        for idx, y in enumerate(y_axes):
            fig.add_trace(
                go.Scatter(
                    x=df_plot[x_axis],
                    y=df_plot[y],
                    mode='lines',
                    name=y,
                    line=dict(color=colors[idx % len(colors)])
                ),
                secondary_y=(idx % 2 == 1)
            )
        
        fig.update_xaxes(title_text=x_axis)
        fig.update_yaxes(title_text="Primary Y", secondary_y=False)
        fig.update_yaxes(title_text="Secondary Y", secondary_y=True)
        fig.update_layout(title="Multi-Axis Line Chart", template=theme)

elif chart_type == "Area Chart" and y_axes:
    if len(y_axes) == 1:
        fig = px.area(
            df_plot,
            x=x_axis,
            y=y_axes[0],
            color=color_by,
            title=f"{y_axes[0]} Area Chart",
            template=theme
        )
    else:
        fig = go.Figure()
        colors = px.colors.qualitative.Plotly
        
        for idx, y in enumerate(y_axes):
            fig.add_trace(go.Scatter(
                x=df_plot[x_axis],
                y=df_plot[y],
                mode='lines',
                name=y,
                fill='tonexty' if idx > 0 else 'tozeroy',
                line=dict(color=colors[idx % len(colors)]),
                opacity=0.7
            ))
        
        fig.update_layout(
            title="Stacked Area Chart",
            xaxis_title=x_axis,
            yaxis_title="Values",
            template=theme
        )

elif chart_type == "Bar Chart" and y_axes:
    fig = px.bar(
        df_plot,
        x=x_axis,
        y=y_axes[0],
        color=color_by,
        title=f"{y_axes[0]} Bar Chart",
        template=theme
    )

elif chart_type == "Scatter Plot" and y_axes:
    fig = px.scatter(
        df_plot,
        x=x_axis,
        y=y_axes[0],
        color=color_by,
        size=size_by,
        title=f"Scatter: {y_axes[0]} vs {x_axis}",
        template=theme,
        hover_data=df_plot.columns
    )

elif chart_type == "Box Plot" and y_axes:
    # Reshape data for box plot
    fig = go.Figure()
    
    for y in y_axes:
        if color_by:
            for group in df_plot[color_by].unique():
                df_group = df_plot[df_plot[color_by] == group]
                fig.add_trace(go.Box(
                    y=df_group[y],
                    name=f"{y} - {group}",
                    boxmean='sd'
                ))
        else:
            fig.add_trace(go.Box(
                y=df_plot[y],
                name=y,
                boxmean='sd'
            ))
    
    fig.update_layout(
        title="Box Plot Analysis",
        yaxis_title="Values",
        template=theme,
        showlegend=True
    )

elif chart_type == "Histogram" and y_axes:
    if len(y_axes) == 1:
        fig = px.histogram(
            df_plot,
            x=y_axes[0],
            color=color_by,
            marginal="box",
            title=f"Distribution of {y_axes[0]}",
            template=theme,
            nbins=30
        )
    else:
        # Multiple histograms
        fig = make_subplots(
            rows=len(y_axes),
            cols=1,
            subplot_titles=y_axes,
            shared_xaxes=False
        )
        
        colors = px.colors.qualitative.Plotly
        for idx, y in enumerate(y_axes):
            fig.add_trace(
                go.Histogram(
                    x=df_plot[y],
                    name=y,
                    marker_color=colors[idx % len(colors)],
                    nbinsx=30
                ),
                row=idx+1,
                col=1
            )
        
        fig.update_layout(
            title="Distribution Analysis",
            template=theme,
            showlegend=True
        )

elif chart_type == "Heatmap":
    # Correlation heatmap
    corr_matrix = df_plot[numeric_columns].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title="Correlation Heatmap",
        template=theme,
        width=800,
        height=800
    )

elif chart_type == "3D Scatter":
    fig = px.scatter_3d(
        df_plot,
        x=x_axis,
        y=y_axes[0],
        z=y_axes[1],
        color=color_by,
        title=f"3D Scatter: {x_axis} vs {y_axes[0]} vs {y_axes[1]}",
        template=theme,
        hover_data=df_plot.columns
    )
    
    fig.update_layout(
        scene=dict(
            xaxis_title=x_axis,
            yaxis_title=y_axes[0],
            zaxis_title=y_axes[1]
        )
    )

elif chart_type == "Violin Plot" and y_axes:
    fig = go.Figure()
    
    for y in y_axes:
        if color_by:
            for group in df_plot[color_by].unique():
                df_group = df_plot[df_plot[color_by] == group]
                fig.add_trace(go.Violin(
                    y=df_group[y],
                    name=f"{y} - {group}",
                    box_visible=True,
                    meanline_visible=True
                ))
        else:
            fig.add_trace(go.Violin(
                y=df_plot[y],
                name=y,
                box_visible=True,
                meanline_visible=True
            ))
    
    fig.update_layout(
        title="Violin Plot Analysis",
        yaxis_title="Values",
        template=theme,
        showlegend=True
    )

elif chart_type == "Sunburst":
    # Create hierarchical data for sunburst
    st.info("📊 Sunburst chart shows data composition and hierarchy")
    
    # Example: Show data distribution by hour and device
    df_sunburst = df_plot.copy()
    df_sunburst['hour'] = pd.to_datetime(df_sunburst['timestamp_local_dt']).dt.hour
    df_sunburst['period'] = df_sunburst['hour'].apply(
        lambda x: 'Morning' if 6 <= x < 12 else 
                  'Afternoon' if 12 <= x < 18 else 
                  'Evening' if 18 <= x < 24 else 'Night'
    )
    
    # Calculate mean temperature for sizing
    if 'temperature' in df_sunburst.columns:
        value_col = 'temperature'
    else:
        value_col = numeric_columns[0]
    
    df_grouped = df_sunburst.groupby(['period', 'deviceName'])[value_col].mean().reset_index()
    
    fig = px.sunburst(
        df_grouped,
        path=['period', 'deviceName'],
        values=value_col,
        title=f"Data Distribution by Time Period",
        template=theme
    )

else:
    st.error("Please select appropriate variables for the chosen chart type")
    st.stop()

# Update layout with common settings
if 'fig' in locals():
    fig.update_layout(
        height=chart_height,
        hovermode='x unified' if x_axis == 'timestamp_local_dt' else 'closest',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add animation if enabled
    if animate and x_axis == 'timestamp_local_dt':
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    showactive=False,
                    buttons=[
                        dict(label="Play",
                             method="animate",
                             args=[None, {"frame": {"duration": 100}}]),
                        dict(label="Pause",
                             method="animate",
                             args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}])
                    ],
                    x=0,
                    y=1.1
                )
            ]
        )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Show statistics below chart
    if y_axes:
        with st.expander("📊 Quick Statistics"):
            stats_cols = st.columns(len(y_axes) if len(y_axes) <= 4 else 4)
            
            for idx, y in enumerate(y_axes[:4]):  # Show max 4 variables
                with stats_cols[idx % len(stats_cols)]:
                    if y in df_plot.columns:
                        st.metric(
                            label=f"{y}",
                            value=f"{df_plot[y].mean():.2f}",
                            delta=f"σ={df_plot[y].std():.2f}"
                        )
                        st.caption(f"Min: {df_plot[y].min():.2f}")
                        st.caption(f"Max: {df_plot[y].max():.2f}")
    
    # Show data table if requested
    if show_table:
        with st.expander("📋 View Data Table"):
            # Show only relevant columns
            display_cols = ['timestamp_local_dt'] if 'timestamp_local_dt' in df_plot.columns else []
            display_cols.extend([col for col in y_axes if col in df_plot.columns])
            if color_by and color_by in df_plot.columns:
                display_cols.append(color_by)
            
            st.dataframe(
                df_plot[display_cols].tail(100),
                use_container_width=True,
                height=400
            )
            
            # Download button
            csv = df_plot[display_cols].to_csv(index=False)
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv,
                file_name=f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# --- 5. Chart Comparison Mode ---
if st.session_state.comparison_mode:
    st.divider()
    st.subheader("🔄 Comparison Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📊 SmartFarm Latest Stats")
        if not df_smartfarm.empty:
            latest_sf = df_smartfarm.iloc[-1]
            st.metric("Temperature", f"{latest_sf['temperature']:.2f} °C")
            st.metric("Humidity", f"{latest_sf['humidity']:.2f} %")
            if 'vpd' in latest_sf:
                st.metric("VPD", f"{latest_sf['vpd']:.3f} kPa")
    
    with col2:
        st.info("🖥️ Raspberry Pi Latest Stats")
        if not df_rpi.empty:
            latest_rpi = df_rpi.iloc[-1]
            st.metric("CPU Temp", f"{latest_rpi['cpu_temp']:.1f} °C")
            st.metric("CPU Usage", f"{latest_rpi['cpu_percent']:.1f} %")
            st.metric("Memory", f"{latest_rpi['memory_percent']:.1f} %")

# --- 6. Chart Templates/Presets ---
st.divider()
st.subheader("📌 Quick Chart Templates")

template_cols = st.columns(4)

with template_cols[0]:
    if st.button("🌡️ Temp & Humidity", use_container_width=True):
        st.session_state.preset = "temp_humidity"
        st.rerun()

with template_cols[1]:
    if st.button("🌱 Soil Analysis", use_container_width=True):
        st.session_state.preset = "soil"
        st.rerun()

with template_cols[2]:
    if st.button("🖥️ System Health", use_container_width=True):
        st.session_state.preset = "system"
        st.rerun()

with template_cols[3]:
    if st.button("📊 Correlation Matrix", use_container_width=True):
        st.session_state.preset = "correlation"
        st.rerun()

# Apply preset if selected
if 'preset' in st.session_state:
    if st.session_state.preset == "temp_humidity":
        st.info("📈 Showing Temperature & Humidity Analysis")
        # Auto-configure for temp & humidity
    elif st.session_state.preset == "soil":
        st.info("🌱 Showing Soil Moisture Analysis")
        # Auto-configure for soil
    elif st.session_state.preset == "system":
        st.info("🖥️ Showing System Performance")
        # Auto-configure for system metrics
    elif st.session_state.preset == "correlation":
        st.info("📊 Showing Correlation Analysis")
        # Auto-configure for correlation
    
    del st.session_state.preset