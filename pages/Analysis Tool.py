import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import load_data_from_api, calculate_vpd, calculate_statistics
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time, timedelta
import numpy as np

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Analysis Tool | SmartFarm Dashboard",
    page_icon="🔬",
    layout="wide"
)

# --- 2. Initialize Session State ---
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'is_filtered' not in st.session_state:
    st.session_state.is_filtered = False
if 'start_datetime_filter' not in st.session_state:
    st.session_state.start_datetime_filter = datetime.now() - timedelta(days=1)
if 'end_datetime_filter' not in st.session_state:
    st.session_state.end_datetime_filter = datetime.now()
if 'data_source' not in st.session_state:
    st.session_state.data_source = "SmartFarm"
if 'selected_stats' not in st.session_state:
    st.session_state.selected_stats = ['mean', 'std', '50%', 'max']
if 'chart_type' not in st.session_state:
    st.session_state.chart_type = "Line Chart"

# --- 3. Auto-Refresh Control ---
if not st.session_state.is_paused:
    st_autorefresh(interval=5000, key="analysis_refresh")

# --- 4. Main Title ---
st.title("🔬 Advanced Analysis Tool")
st.caption("A flexible, Power BI-like tool for in-depth data exploration.")

# --- 5. UNIFIED SIDEBAR (CONTROL PANEL) ---
with st.sidebar:
    st.header("🎛️ Control Panel")

    st.subheader("📁 Data Source")
    st.selectbox("Select a data source:", ["SmartFarm", "Raspberry Pi"], key='data_source')
    st.divider()

    st.subheader("⏱️ Real-time Control")
    if st.button("⏸️ Pause Refresh" if not st.session_state.is_paused else "▶️ Resume Refresh", width='stretch', type="primary" if st.session_state.is_paused else "secondary"):
        st.session_state.is_paused = not st.session_state.is_paused
        st.rerun()
    st.info("Status: " + ("PAUSED 🔴" if st.session_state.is_paused else "ACTIVE 🟢"))
    st.divider()

    st.subheader("📅 Time Range Filter")
    filter_type = st.radio("Filter Type:", ["Date Range", "Quick Select"], index=1, horizontal=True)

    temp_start_date = st.session_state.start_datetime_filter.date()
    temp_end_date = st.session_state.end_datetime_filter.date()
    temp_start_time = st.session_state.start_datetime_filter.time()
    temp_end_time = st.session_state.end_datetime_filter.time()

    if filter_type == "Date Range":
        user_date_range = st.date_input("Select Date Range", value=(temp_start_date, temp_end_date))
        if len(user_date_range) == 2:
            temp_start_date, temp_end_date = user_date_range
        elif len(user_date_range) == 1:
            temp_start_date = temp_end_date = user_date_range[0]
        c1, c2 = st.columns(2)
        with c1: temp_start_time = st.time_input("Start Time", value=temp_start_time)
        with c2: temp_end_time = st.time_input("End Time", value=temp_end_time)
    else: # Quick Select
        quick_option = st.selectbox("Quick Select:", ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days"])
        now = datetime.now()
        start_dt, end_dt = now - timedelta(hours=1), now
        if quick_option == "Last 6 Hours": start_dt = now - timedelta(hours=6)
        elif quick_option == "Last 24 Hours": start_dt = now - timedelta(days=1)
        elif quick_option == "Last 3 Days": start_dt = now - timedelta(days=3)
        elif quick_option == "Last 7 Days": start_dt = now - timedelta(days=7)
        temp_start_date, temp_end_date = start_dt.date(), end_dt.date()
        temp_start_time, temp_end_time = start_dt.time(), end_dt.time()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Apply Filter", width='stretch', type="primary"):
            st.session_state.start_datetime_filter = datetime.combine(temp_start_date, temp_start_time)
            st.session_state.end_datetime_filter = datetime.combine(temp_end_date, temp_end_time)
            st.session_state.is_filtered = True
            st.rerun()
    with c2:
        if st.button("🔄 Clear Filter", width='stretch'):
            st.session_state.is_filtered = False
            st.rerun()
    st.divider()

    st.subheader("📊 Chart Builder")
    chart_types = { "Line Chart": "📈", "Area Chart": "🏔️", "Bar Chart": "📊", "Scatter Plot": "🎯", "Box Plot": "📦", "Histogram": "📊", "Heatmap": "🔥"}
    st.selectbox("Chart Type:", list(chart_types.keys()), key='chart_type', format_func=lambda x: f"{chart_types[x]} {x}")

# --- 6. Load and Filter Data ---
@st.cache_data(ttl=60 if not st.session_state.is_paused else 3600)
def load_full_data(source):
    # This is the corrected function call
    df = load_data_from_api(source)
    if source == "SmartFarm" and not df.empty:
        # Perform calculations after loading
        df['vpd'] = df.apply(lambda row: calculate_vpd(row['temperature'], row['humidity']), axis=1)
    return df

df_full = load_full_data(st.session_state.data_source)

if '_id' in df_full.columns:
    df_full = df_full.drop(columns=['_id'])
if df_full.empty:
    st.error(f"❌ No data found for '{st.session_state.data_source}' in the last 7 days.")
    st.stop()

if st.session_state.is_filtered:
    start_filter, end_filter = st.session_state.start_datetime_filter, st.session_state.end_datetime_filter
else:
    start_filter, end_filter = datetime.now() - timedelta(days=1), datetime.now()

df_display = df_full[(df_full['timestamp_local_dt'] >= start_filter) & (df_full['timestamp_local_dt'] <= end_filter)].copy()
if df_display.empty:
    st.warning("No data available for the selected time range. Try expanding the filter.")
    st.stop()

# --- 7. DYNAMIC SIDEBAR WIDGETS (Continued) ---
numeric_columns = df_display.select_dtypes(include=np.number).columns.tolist()

with st.sidebar:
    st.write("**Axis Configuration**")
    chart_type = st.session_state.chart_type
    if chart_type in ["Line Chart", "Area Chart", "Bar Chart", "Scatter Plot"]:
        x_axis = st.selectbox("X-Axis:", ['timestamp_local_dt'] + numeric_columns, index=0)
        y_axes_options = [col for col in numeric_columns if col != x_axis]
        if chart_type in ["Line Chart", "Area Chart"]: y_axes = st.multiselect("Y-Axis:", y_axes_options, default=y_axes_options[:1])
        else: y_axes = [st.selectbox("Y-Axis:", y_axes_options)]
        color_by = st.selectbox("Color By:", [None] + [col for col in df_display.columns if df_display[col].dtype == 'object'])
    elif chart_type in ["Histogram", "Box Plot"]:
        x_axis, color_by = None, None
        y_axes = st.multiselect("Variables:", numeric_columns, default=numeric_columns[:1])
    elif chart_type == "Heatmap":
        x_axis, color_by = None, None
        y_axes = st.multiselect("Variables:", numeric_columns, default=numeric_columns)
    else: x_axis, y_axes, color_by = None, [], None

    with st.expander("⚙️ Advanced Options"):
        if chart_type in ["Line Chart", "Bar Chart", "Area Chart"] and x_axis == 'timestamp_local_dt':
            aggregation = st.selectbox("Time Aggregation:", ["None", "1min", "5min", "15min", "30min", "1H", "1D"])
            if aggregation != "None": agg_function = st.selectbox("Function:", ["mean", "sum", "max", "min", "median", "std"])
            else: agg_function = "mean"
        else: aggregation, agg_function = "None", "mean"
        show_table = st.checkbox("Show Raw Data Table")
        available_stats = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'variance', 'skewness']
        st.multiselect("Statistics for Table:", available_stats, key='selected_stats')

# --- 8. Main Content Area ---
if st.session_state.is_filtered:
    st.info(f"📅 Displaying data from **{start_filter:%Y-%m-%d %H:%M}** to **{end_filter:%Y-%m-%d %H:%M}**")
else:
    st.info(f"📊 Displaying default data: **Last 24 hours**.")

st.subheader("📈 Key Metrics for Selected Range")
display_vars = y_axes if y_axes else numeric_columns[:4]
cols = st.columns(min(len(display_vars), 4))
for i, var in enumerate(display_vars[:4]):
    if var in df_display.columns:
        with cols[i]: st.metric(f"{var.replace('_', ' ').title()}", f"{df_display[var].mean():.2f}", f"σ={df_display[var].std():.2f}")
st.divider()

if aggregation != "None" and x_axis == 'timestamp_local_dt':
    try:
        df_plot = df_display.set_index('timestamp_local_dt')[numeric_columns].resample(aggregation).agg(agg_function).reset_index()
        st.success(f"✅ Data aggregated by **{aggregation}** using **{agg_function}**.")
    except Exception as e:
        st.error(f"Aggregation failed: {e}"); df_plot = df_display.copy()
else:
    df_plot = df_display.copy()

st.subheader(f"📊 {chart_type}")
if not y_axes: st.warning("Please select at least one variable for the Y-Axis in the sidebar."); st.stop()
fig = None
if chart_type == "Line Chart": fig = px.line(df_plot, x=x_axis, y=y_axes, color=color_by, title=f"Line Chart: {', '.join(y_axes)}")
elif chart_type == "Area Chart": fig = px.area(df_plot, x=x_axis, y=y_axes, color=color_by, title=f"Area Chart: {', '.join(y_axes)}")
elif chart_type == "Bar Chart": fig = px.bar(df_plot, x=x_axis, y=y_axes[0], color=color_by, title=f"Bar Chart: {y_axes[0]}")
elif chart_type == "Scatter Plot": fig = px.scatter(df_plot, x=x_axis, y=y_axes[0], color=color_by, title=f"Scatter Plot: {y_axes[0]} vs {x_axis}")
elif chart_type == "Box Plot": fig = px.box(df_plot, y=y_axes, title="Box Plot Analysis")
elif chart_type == "Histogram": fig = px.histogram(df_plot, x=y_axes[0], marginal="box", title=f"Distribution of {y_axes[0]}")
elif chart_type == "Heatmap":
    if len(y_axes) < 2: st.warning("Heatmap requires at least 2 variables."); st.stop()
    corr_matrix = df_plot[y_axes].corr()
    fig = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', aspect='auto', title="Correlation Heatmap")

if fig:
    fig.update_layout(height=600, template="plotly_white", legend_title_text='')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Could not generate the selected chart.")
if show_table:
    with st.expander("📋 Raw Data Table", expanded=True):
        st.dataframe(df_display, use_container_width=True)
        csv_export = df_display.to_csv().encode('utf-8')
        st.download_button("📥 Download Displayed Data (CSV)", csv_export, "data_export.csv", "text/csv")

st.divider()
st.subheader("🔬 In-Depth Analysis")
tab1, tab2, tab3 = st.tabs(["📋 Statistics", "📈 Distribution", "🔥 Correlation"])
with tab1:
    if y_axes:
        stats_df = calculate_statistics(df_display, y_axes)
        display_stats = stats_df.loc[stats_df.index.intersection(st.session_state.selected_stats)]
        st.dataframe(display_stats.style.format("{:.3f}"), use_container_width=True)
        st.download_button("📥 Download Statistics (CSV)", display_stats.to_csv().encode('utf-8'), f"stats.csv", "text/csv")
with tab2:
    if y_axes:
        for var in y_axes[:3]:
            fig_dist = px.histogram(df_display, x=var, marginal="box", title=f"Distribution of {var}")
            st.plotly_chart(fig_dist, use_container_width=True)
with tab3:
    if len(y_axes) >= 2:
        corr_matrix = df_display[y_axes].corr()
        fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', title="Correlation Matrix")
        st.plotly_chart(fig_corr, use_container_width=True)

