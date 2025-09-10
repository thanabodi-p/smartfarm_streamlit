# pages/02_Analysis_Tool.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import load_data_from_mongo, calculate_vpd, get_vpd_status
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Analysis Tool | SmartFarm Dashboard", 
    page_icon="🔬",
    layout="wide"
)

# --- 2. Initialize Session State (The Correct Way) ---
# We manage the state of the filter using these clear variables.
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'is_filtered' not in st.session_state:
    st.session_state.is_filtered = False

# These are the *only* states needed for the time filter.
# They store the final, applied filter values.
if 'start_datetime_filter' not in st.session_state:
    st.session_state.start_datetime_filter = datetime.now() - timedelta(days=1)
if 'end_datetime_filter' not in st.session_state:
    st.session_state.end_datetime_filter = datetime.now()

# Other states
if 'data_source' not in st.session_state:
    st.session_state.data_source = "SmartFarm"
if 'selected_stats' not in st.session_state:
    st.session_state.selected_stats = ['mean', 'std', '50%', 'max']

# --- Auto-refresh control ---
if not st.session_state.is_paused:
    st_autorefresh(interval=5000, key="analysis_refresh")

# --- Main Title ---
st.title("🔬 In-Depth Analysis")
st.caption("Advanced Data Analysis Tool with Real-time Capabilities")

# --- 5. Sidebar (Control Panel) ---
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # Data Source Selection
    st.subheader("📁 Data Source")
    st.selectbox("Select a data source:", ["SmartFarm", "Raspberry Pi"], key='data_source')
    st.divider()

    # Real-time Control
    st.subheader("⏱️ Real-time Control")
    if st.button("⏸️ Pause Refresh" if not st.session_state.is_paused else "▶️ Resume Refresh", width='stretch', type="primary" if st.session_state.is_paused else "secondary"):
        st.session_state.is_paused = not st.session_state.is_paused
        st.rerun()
    st.info("Status: " + ("PAUSED 🔴" if st.session_state.is_paused else "ACTIVE 🟢"))
    st.divider()

    # --- Time Range Filter (Simplified) ---
    st.subheader("📅 Time Range Filter")
    filter_type = st.radio("Filter Type:", ["Date Range", "Quick Select"], index=1)

    # These are temporary variables to hold user input from widgets
    # They are reset on each rerun.
    temp_start_date = st.session_state.start_datetime_filter.date()
    temp_end_date = st.session_state.end_datetime_filter.date()
    temp_start_time = st.session_state.start_datetime_filter.time()
    temp_end_time = st.session_state.end_datetime_filter.time()

    if filter_type == "Date Range":
        # Date range selection - can be same day or different days
        user_date_range = st.date_input("Select Date Range", value=(temp_start_date, temp_end_date))
        if len(user_date_range) == 2:
            temp_start_date, temp_end_date = user_date_range
        elif len(user_date_range) == 1:
            # If only one date selected, use it for both start and end
            temp_start_date = temp_end_date = user_date_range[0]
        
        # Time selection for precise control
        c1, c2 = st.columns(2)
        with c1:
            temp_start_time = st.time_input("Start Time", value=temp_start_time)
        with c2:
            temp_end_time = st.time_input("End Time", value=temp_end_time)

    else: # Quick Select
        quick_option = st.selectbox("Quick Select:", ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days"])
        now = datetime.now()
        if quick_option == "Last 1 Hour":
            start_dt, end_dt = now - timedelta(hours=1), now
        elif quick_option == "Last 6 Hours":
            start_dt, end_dt = now - timedelta(hours=6), now
        elif quick_option == "Last 24 Hours":
            start_dt, end_dt = now - timedelta(days=1), now
        elif quick_option == "Last 3 Days":
            start_dt, end_dt = now - timedelta(days=3), now
        else: # Last 7 Days
            start_dt, end_dt = now - timedelta(days=7), now
            
        temp_start_date, temp_end_date = start_dt.date(), end_dt.date()
        temp_start_time, temp_end_time = start_dt.time(), end_dt.time()

    # --- Apply and Clear Buttons ---
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Apply Filter", width='stretch', type="primary"):
            # ## <-- KEY CHANGE: Combine temp variables and save to session state
            st.session_state.start_datetime_filter = datetime.combine(temp_start_date, temp_start_time)
            st.session_state.end_datetime_filter = datetime.combine(temp_end_date, temp_end_time)
            st.session_state.is_filtered = True
            st.rerun()
    with c2:
        if st.button("🔄 Clear Filter", width='stretch'):
            st.session_state.is_filtered = False
            # We don't need to reset anything else, the logic below will handle it
            st.rerun()
    
    st.divider()
    
    # 4. Chart Builder
    st.subheader("📊 Chart Builder")
    
    chart_types = {
        "Line Chart": "📈",
        "Area Chart": "🏔️",
        "Bar Chart": "📊",
        "Scatter Plot": "🎯",
        "Box Plot": "📦",
        "Histogram": "📊",
        "Heatmap": "🔥"
    }
    
    chart_type = st.selectbox(
        "Chart Type:",
        list(chart_types.keys()),
        format_func=lambda x: f"{chart_types[x]} {x}"
    )

# --- Load Data Based on Selection ---
# --- 6. Load and Filter Data ---
@st.cache_data(ttl=60 if not st.session_state.is_paused else 3600)
def load_full_data(source):
    if source == "SmartFarm":
        return load_data_from_mongo("telemetry_data_clean", "SmartFarm", time_delta_days=7)
    elif source == "Raspberry Pi":
        return load_data_from_mongo("raspberry_pi_telemetry_clean", "raspberry_pi_status", time_delta_days=7)
    return pd.DataFrame()

df_full = load_full_data(st.session_state.data_source)
# Remove the MongoDB ObjectId column as it's not serializable for plotting
if '_id' in df_full.columns:
    df_full = df_full.drop(columns=['_id'])

if df_full.empty:
    st.error(f"❌ No data found for '{st.session_state.data_source}' in the last 7 days.")
    st.stop()

# ## <-- KEY CHANGE: Filtering logic is now simpler and cleaner
if st.session_state.is_filtered:
    start_filter, end_filter = st.session_state.start_datetime_filter, st.session_state.end_datetime_filter
else:
    start_filter, end_filter = datetime.now() - timedelta(days=1), datetime.now()


df_display = df_full[
    (df_full['timestamp_local_dt'] >= start_filter) &
    (df_full['timestamp_local_dt'] <= end_filter)
].copy()

if df_display.empty:
    st.warning("No data available for the selected time range. Try expanding the filter.")
    st.stop()

# Get numeric columns for analysis
numeric_columns = df_display.select_dtypes(include=np.number).columns.tolist()

with st.sidebar:
    st.write("**Axis Configuration**")
    if chart_type in ["Line Chart", "Area Chart", "Bar Chart", "Scatter Plot"]:
        x_axis = st.selectbox("X-Axis:", ['timestamp_local_dt'] + numeric_columns, index=0)
        y_axes_options = [col for col in numeric_columns if col != x_axis]
        if chart_type in ["Line Chart", "Area Chart"]:
            y_axes = st.multiselect("Y-Axis:", y_axes_options, default=y_axes_options[0] if y_axes_options else [])
        else:
            y_axes = [st.selectbox("Y-Axis:", y_axes_options)]
        color_by = st.selectbox("Color By:", [None] + [col for col in df_display.columns if df_display[col].dtype == 'object'])
    elif chart_type in ["Histogram", "Box Plot"]:
        x_axis, color_by = None, None
        y_axes = st.multiselect("Variables:", numeric_columns, default=numeric_columns[0] if numeric_columns else [])
    elif chart_type == "Heatmap":
        x_axis, color_by = None, None
        y_axes = st.multiselect("Variables:", numeric_columns, default=numeric_columns)
    else:
        x_axis, y_axes, color_by = None, [], None

    with st.expander("⚙️ Advanced Options"):
        if chart_type in ["Line Chart", "Bar Chart", "Area Chart"] and x_axis == 'timestamp_local_dt':
            aggregation = st.selectbox("Time Aggregation:", ["None", "1min", "5min", "15min", "30min", "1H", "1D"])
            if aggregation != "None":
                agg_function = st.selectbox("Function:", ["mean", "sum", "max", "min", "median", "std"])
            else: agg_function = "mean"
        else: aggregation, agg_function = "None", "mean"
        show_table = st.checkbox("Show Raw Data Table")
        available_stats = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', 'variance', 'skewness']
        st.multiselect("Statistics for Table:", available_stats, key='selected_stats')


# --- Main Content Area ---

# Time range info
if st.session_state.is_filtered:
    st.info(f"📅 Displaying data from **{start_filter:%Y-%m-%d %H:%M}** to **{end_filter:%Y-%m-%d %H:%M}**")
else:
    st.info(f"📊 Displaying default data: **Last 24 hours**.")

st.subheader("📈 Key Metrics for Selected Range")
display_vars = y_axes if y_axes else numeric_columns[:4]
cols = st.columns(min(len(display_vars), 4))
for i, var in enumerate(display_vars[:4]):
    if var in df_display.columns:
        with cols[i]:
            st.metric(f"{var.replace('_', ' ').title()}", f"{df_display[var].mean():.2f}", f"σ={df_display[var].std():.2f}")

st.divider()

# --- Apply Time Aggregation if Needed ---
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
if chart_type == "Line Chart":
    fig = px.line(df_plot, x=x_axis, y=y_axes, color=color_by, title=f"{', '.join(y_axes)} vs {x_axis}")
elif chart_type == "Area Chart":
    fig = px.area(df_plot, x=x_axis, y=y_axes, color=color_by, title=f"{', '.join(y_axes)} vs {x_axis}")
elif chart_type == "Bar Chart":
    fig = px.bar(df_plot, x=x_axis, y=y_axes[0], color=color_by, title=f"{y_axes[0]} vs {x_axis}")
elif chart_type == "Scatter Plot":
    fig = px.scatter(df_plot, x=x_axis, y=y_axes[0], color=color_by, title=f"{y_axes[0]} vs {x_axis}", hover_data=df_plot.columns)
elif chart_type == "Box Plot":
    fig = px.box(df_plot, y=y_axes, title="Box Plot Analysis")
elif chart_type == "Histogram":
    fig = px.histogram(df_plot, x=y_axes[0], marginal="box", title=f"Distribution of {y_axes[0]}")
elif chart_type == "Heatmap":
    if len(y_axes) < 2: st.warning("Heatmap requires at least 2 variables."); st.stop()
    corr_matrix = df_plot[y_axes].corr()
    fig = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', aspect='auto', title="Correlation Heatmap")

if fig:
    fig.update_layout(height=600, template="plotly_white", legend_title_text='')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Could not generate the selected chart.")

# --- Analysis Tabs ---
st.divider()
st.subheader("🔬 Advanced Analysis Tool")

tab1, tab2, tab3 = st.tabs(["📋 Statistics", "📈 Distribution", "🔥 Correlation"])

with tab1:
    st.write("### ตารางสถิติ")
    
    if y_axes:
        # Calculate only selected statistics
        stats_df = pd.DataFrame()
        
        for stat in st.session_state.selected_stats:
            if stat == 'count':
                stats_df[stat] = df_display[y_axes].count()
            elif stat == 'mean':
                stats_df[stat] = df_display[y_axes].mean()
            elif stat == 'std':
                stats_df[stat] = df_display[y_axes].std()
            elif stat == 'min':
                stats_df[stat] = df_display[y_axes].min()
            elif stat == '25%':
                stats_df[stat] = df_display[y_axes].quantile(0.25)
            elif stat == '50%':
                stats_df[stat] = df_display[y_axes].median()
            elif stat == '75%':
                stats_df[stat] = df_display[y_axes].quantile(0.75)
            elif stat == 'max':
                stats_df[stat] = df_display[y_axes].max()
            elif stat == 'variance':
                stats_df[stat] = df_display[y_axes].var()
            elif stat == 'skewness':
                stats_df[stat] = df_display[y_axes].skew()
        
        # Transpose for better display
        stats_df = stats_df.T
        
        # Style the dataframe
        styled_stats = stats_df.style.format("{:.3f}")
        
        # Apply gradient coloring based on stat type
        if 'std' in stats_df.index or 'variance' in stats_df.index:
            bad_stats = [s for s in ['std', 'variance'] if s in stats_df.index]
            styled_stats = styled_stats.background_gradient(
                cmap='RdYlGn_r',
                subset=pd.IndexSlice[bad_stats, :],
                axis=1
            )
        
        if 'mean' in stats_df.index or 'max' in stats_df.index:
            good_stats = [s for s in ['mean', '50%', 'max'] if s in stats_df.index]
            styled_stats = styled_stats.background_gradient(
                cmap='RdYlGn',
                subset=pd.IndexSlice[good_stats, :],
                axis=1
            )
        
        st.dataframe(styled_stats, use_container_width=True)
        
        # Download button
        csv = stats_df.to_csv()
        st.download_button(
            label="📥 ดาวน์โหลดสถิติ (CSV)",
            data=csv,
            file_name=f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with tab2:
    st.write("### การกระจายของข้อมูล")
    
    if y_axes:
        for var in y_axes[:3]:  # Show max 3 distributions
            if var in df_display.columns:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_hist = px.histogram(
                        df_display,
                        x=var,
                        nbins=30,
                        title=f"Histogram: {var}"
                    )
                    fig_hist.update_layout(height=300)
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col2:
                    fig_box = px.box(
                        df_display,
                        y=var,
                        title=f"Box Plot: {var}"
                    )
                    fig_box.update_layout(height=300)
                    st.plotly_chart(fig_box, use_container_width=True)

with tab3:
    st.write("### ความสัมพันธ์ระหว่างตัวแปร")
    
    if len(y_axes) >= 2:
        corr_matrix = df_display[y_axes].corr()
        
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale='RdBu',
            aspect='auto',
            title="Correlation Matrix"
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Correlation insights
        st.info("💡 **ข้อมูลเชิงลึก:**")
        for i in range(len(corr_matrix)):
            for j in range(i+1, len(corr_matrix)):
                corr_val = corr_matrix.iloc[i, j]
                var1 = corr_matrix.index[i]
                var2 = corr_matrix.columns[j]
                
                if abs(corr_val) > 0.7:
                    strength = "สูง" if abs(corr_val) > 0.8 else "ปานกลาง"
                    direction = "เชิงบวก" if corr_val > 0 else "เชิงลบ"
                    st.write(f"• {var1} และ {var2}: ความสัมพันธ์{direction}{strength} ({corr_val:.3f})")
    else:
        st.info("เลือกตัวแปรอย่างน้อย 2 ตัวเพื่อดูความสัมพันธ์")

# --- Show Data Table if Requested ---
if show_table:
    st.divider()
    with st.expander("📋 ตารางข้อมูลดิบ"):
        # Show relevant columns
        display_cols = ['timestamp_local_dt'] if 'timestamp_local_dt' in df_plot.columns else []
        display_cols.extend([col for col in y_axes if col in df_plot.columns])
        
        if display_cols:
            st.dataframe(
                df_plot[display_cols].tail(100),
                use_container_width=True,
                height=400
            )
            
            # Download button
            csv = df_plot[display_cols].to_csv(index=False)
            st.download_button(
                label="📥 ดาวน์โหลดข้อมูล (CSV)",
                data=csv,
                file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# --- Footer Information ---
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🕐 ข้อมูลล่าสุด: {df_display['timestamp_local_dt'].max().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    st.caption(f"📊 จำนวนข้อมูล: {len(df_display):,} แถว")
with col3:
    if st.session_state.is_paused:
        st.caption("⏸️ หยุดการรีเฟรชชั่วคราว")
    else:
        st.caption("🔄 รีเฟรชอัตโนมัติทุก 5 วินาที")