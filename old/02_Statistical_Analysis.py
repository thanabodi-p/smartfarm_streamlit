# pages/02_Statistical_Analysis.py
import streamlit as st
from datetime import datetime, time, timedelta
from utils import load_data_from_mongo, calculate_vpd
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="Statistical Analysis")
st.title("🔬 Interactive Analysis Dashboard")

# --- 1. Initialize Session State ---
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'is_filtered' not in st.session_state:
    st.session_state.is_filtered = False
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()
if 'start_time' not in st.session_state:
    st.session_state.start_time = time(0, 0)
if 'end_time' not in st.session_state:
    st.session_state.end_time = time(23, 59)
if 'selected_variables' not in st.session_state:
    st.session_state.selected_variables = ['temperature', 'humidity']

# --- 2. Auto-refresh control ---
if not st.session_state.is_paused:
    st_autorefresh(interval=5000, key="data_refresh")

# --- 3. Load Data ---
@st.cache_data(ttl=300 if not st.session_state.is_paused else 3600)
def load_data_cached(is_paused):
    """โหลดข้อมูลโดยมี cache ที่ปรับตามสถานะ pause"""
    return load_data_from_mongo("telemetry_data_clean", "SmartFarm", time_delta_days=7)

df_raw = load_data_cached(st.session_state.is_paused)
df_smartfarm = df_raw[df_raw['deviceName'] == 'SmartFarm'].copy()

# คำนวณ VPD สำหรับทุกแถว
if not df_smartfarm.empty:
    df_smartfarm['vpd'] = df_smartfarm.apply(
        lambda row: calculate_vpd(row['temperature'], row['humidity']), 
        axis=1
    )

# --- 4. Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Pause/Resume Button
    if st.button(
        "⏸️ Pause Auto-refresh" if not st.session_state.is_paused else "▶️ Resume Auto-refresh",
        use_container_width=True,
        type="primary" if st.session_state.is_paused else "secondary"
    ):
        st.session_state.is_paused = not st.session_state.is_paused
        st.rerun()
    
    # Status indicator
    if st.session_state.is_paused:
        st.error("🔴 Auto-refresh is PAUSED")
    else:
        st.success("🟢 Auto-refresh is ACTIVE (5s)")
    
    st.divider()
    
    # Time Filter Section
    st.header("📅 Time Filter")
    
    # Date Range Selection
    filter_type = st.radio(
        "Filter Type:",
        ["Single Day", "Date Range", "Quick Select"],
        index=0
    )
    
    if filter_type == "Single Day":
        selected_date = st.date_input(
            "Select Date",
            value=st.session_state.selected_date,
            max_value=datetime.now().date()
        )
        end_date = selected_date
        
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input(
                "Start Time",
                value=st.session_state.start_time,
                step=60
            )
        with col2:
            end_time = st.time_input(
                "End Time",
                value=st.session_state.end_time,
                step=60
            )
    
    elif filter_type == "Date Range":
        date_range = st.date_input(
            "Select Date Range",
            value=(
                st.session_state.selected_date - timedelta(days=1),
                st.session_state.selected_date
            ),
            max_value=datetime.now().date()
        )
        if len(date_range) == 2:
            selected_date, end_date = date_range
        else:
            selected_date = end_date = date_range[0]
        
        start_time = time(0, 0)
        end_time = time(23, 59)
    
    else:  # Quick Select
        quick_option = st.selectbox(
            "Quick Select:",
            ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days"]
        )
        
        now = datetime.now()
        if quick_option == "Last 1 Hour":
            selected_date = end_date = now.date()
            start_time = (now - timedelta(hours=1)).time()
            end_time = now.time()
        elif quick_option == "Last 6 Hours":
            start_dt = now - timedelta(hours=6)
            selected_date = start_dt.date()
            end_date = now.date()
            start_time = start_dt.time()
            end_time = now.time()
        elif quick_option == "Last 24 Hours":
            start_dt = now - timedelta(days=1)
            selected_date = start_dt.date()
            end_date = now.date()
            start_time = start_dt.time()
            end_time = now.time()
        elif quick_option == "Last 3 Days":
            selected_date = (now - timedelta(days=3)).date()
            end_date = now.date()
            start_time = time(0, 0)
            end_time = time(23, 59)
        else:  # Last 7 Days
            selected_date = (now - timedelta(days=7)).date()
            end_date = now.date()
            start_time = time(0, 0)
            end_time = time(23, 59)
    
    # Apply and Clear buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Apply Filter", use_container_width=True, type="primary"):
            st.session_state.selected_date = selected_date
            st.session_state.start_time = start_time
            st.session_state.end_time = end_time
            st.session_state.is_filtered = True
            st.rerun()
    
    with col2:
        if st.button("🔄 Clear Filter", use_container_width=True):
            st.session_state.is_filtered = False
            st.rerun()
    
    st.divider()
    
    # Variable Selection
    st.header("📊 Variables to Display")
    available_vars = {
        'temperature': '🌡️ Temperature',
        'humidity': '💧 Humidity',
        'vpd': '💨 VPD',
        'soil_raw_1': '🌱 Soil 1',
        'soil_raw_2': '🌱 Soil 2',
        'soil_raw_3': '🌱 Soil 3',
        'soil_raw_4': '🌱 Soil 4'
    }
    
    selected_vars = st.multiselect(
        "Select Variables:",
        options=list(available_vars.keys()),
        default=st.session_state.selected_variables,
        format_func=lambda x: available_vars[x]
    )
    
    if selected_vars != st.session_state.selected_variables:
        st.session_state.selected_variables = selected_vars
        st.rerun()

# --- 5. Main Content Area ---
if df_smartfarm.empty:
    st.warning("❌ No data found from Device 'SmartFarm'")
else:
    # Filter data based on selection
    if st.session_state.is_filtered:
        start_datetime = datetime.combine(selected_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        
        df_display = df_smartfarm[
            (df_smartfarm['timestamp_local_dt'] >= start_datetime) &
            (df_smartfarm['timestamp_local_dt'] <= end_datetime)
        ].copy()
        
        # Header with filter info
        st.info(f"📅 Showing data from **{start_datetime.strftime('%Y-%m-%d %H:%M')}** to **{end_datetime.strftime('%Y-%m-%d %H:%M')}**")
    else:
        df_display = df_smartfarm.copy()
        st.info("📊 Showing all available data (last 7 days)")
    
    if df_display.empty:
        st.warning("No data found in the specified range.")
    else:
        # Metrics Cards
        st.subheader("📈 Current Statistics")
        
        # แสดง metrics สำหรับตัวแปรที่เลือก
        cols = st.columns(len(st.session_state.selected_variables))
        for idx, var in enumerate(st.session_state.selected_variables):
            with cols[idx]:
                latest_val = df_display[var].iloc[-1]
                mean_val = df_display[var].mean()
                delta = latest_val - mean_val
                
                # กำหนด icon และ format
                if var == 'temperature':
                    icon = "🌡️"
                    unit = "°C"
                    val_format = f"{latest_val:.2f}"
                elif var == 'humidity':
                    icon = "💧"
                    unit = "%"
                    val_format = f"{latest_val:.2f}"
                elif var == 'vpd':
                    icon = "💨"
                    unit = "kPa"
                    val_format = f"{latest_val:.3f}"
                else:  # soil sensors
                    icon = "🌱"
                    unit = ""
                    val_format = f"{latest_val:.0f}"
                
                st.metric(
                    label=f"{icon} {var.replace('_', ' ').title()}",
                    value=f"{val_format} {unit}",
                    delta=f"{delta:+.2f} from avg",
                    delta_color="normal"
                )
        
        st.divider()
        
        # Interactive Plotly Charts
        st.subheader("📊 Interactive Time Series Charts")
        
        # Create tabs for different chart types
        tab1, tab2, tab3 = st.tabs(["📈 Line Chart", "📊 Area Chart", "🎯 Scatter Plot"])
        
        with tab1:
            # Line chart with multiple y-axes for different scales
            fig = go.Figure()
            
            # กำหนดสีสำหรับแต่ละตัวแปร
            colors = px.colors.qualitative.Plotly
            
            for idx, var in enumerate(st.session_state.selected_variables):
                fig.add_trace(go.Scatter(
                    x=df_display['timestamp_local_dt'],
                    y=df_display[var],
                    mode='lines',
                    name=var.replace('_', ' ').title(),
                    line=dict(color=colors[idx % len(colors)], width=2),
                    yaxis=f'y{idx+1}' if idx < 2 else 'y2'  # ใช้แกน y หลายแกน
                ))
            
            # Update layout for multiple y-axes
            fig.update_layout(
                title="Time Series Analysis",
                xaxis=dict(title="Time", gridcolor='lightgray'),
                yaxis=dict(title="Temperature/Humidity/VPD", side="left", gridcolor='lightgray'),
                yaxis2=dict(title="Soil Moisture", overlaying="y", side="right", gridcolor='lightgray'),
                hovermode='x unified',
                height=500,
                showlegend=True,
                legend=dict(x=0, y=1.1, orientation="h"),
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Area chart
            fig_area = go.Figure()
            
            for idx, var in enumerate(st.session_state.selected_variables):
                fig_area.add_trace(go.Scatter(
                    x=df_display['timestamp_local_dt'],
                    y=df_display[var],
                    mode='lines',
                    name=var.replace('_', ' ').title(),
                    fill='tonexty' if idx > 0 else 'tozeroy',
                    line=dict(width=1),
                    opacity=0.6
                ))
            
            fig_area.update_layout(
                title="Stacked Area Chart",
                xaxis_title="Time",
                yaxis_title="Values",
                hovermode='x unified',
                height=500,
                template="plotly_white"
            )
            
            st.plotly_chart(fig_area, use_container_width=True)
        
        with tab3:
            # Scatter plot matrix for correlation
            if len(st.session_state.selected_variables) >= 2:
                fig_scatter = px.scatter_matrix(
                    df_display[st.session_state.selected_variables],
                    dimensions=st.session_state.selected_variables,
                    color=df_display.index % 10,  # Color by time segments
                    title="Variable Relationships",
                    height=600
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Select at least 2 variables to see correlation scatter plot")
        
        st.divider()
        
        # Statistical Summary with Enhanced Display
        st.subheader("📊 Statistical Summary")
        
        # Create tabs for different statistical views
        stat_tab1, stat_tab2, stat_tab3 = st.tabs(["📋 Summary Stats", "📈 Distribution", "🔥 Heatmap"])
        
        with stat_tab1:
            stats = df_display[st.session_state.selected_variables].describe()
            
            # เพิ่ม variance และ skewness
            stats.loc['variance'] = df_display[st.session_state.selected_variables].var()
            stats.loc['skewness'] = df_display[st.session_state.selected_variables].skew()
            
            # --- เริ่มการแก้ไขตรงนี้ ---
            
            # 1. สร้าง Styler object ก่อน
            s = stats.style.format("{:.3f}")
            
            # 2. กำหนดแถวที่ "ค่าสูงคือไม่ดี" (ต้องการให้เป็นสีแดง)
            # เราจะใช้ colormap แบบกลับด้าน '_r' (เช่น RdYlGn_r)
            bad_high_stats = ['std', 'variance'] 
            s.background_gradient(
                cmap='RdYlGn_r',  # สังเกต _r เพื่อกลับด้านสี
                subset=pd.IndexSlice[bad_high_stats, :], 
                axis=1
            )
            
            # 3. กำหนดแถวที่ "ค่าสูงคือปกติ/ดี"
            # เราใช้ colormap ปกติ
            normal_stats = ['count', 'mean', 'min', '25%', '50%', '75%', 'max']
            # กรองเอาเฉพาะแถวที่มีอยู่ใน stats จริงๆ
            normal_stats_exist = [stat for stat in normal_stats if stat in stats.index]
            s.background_gradient(
                cmap='RdYlGn', 
                subset=pd.IndexSlice[normal_stats_exist, :], 
                axis=0
            )
            
            # (Optional) สำหรับ skewness, ค่าใกล้ 0 คือดีที่สุด อาจใช้สีที่ต่างออกไป
            # เช่น 'coolwarm' ที่มีสีกลางเป็นสีขาว
            s.background_gradient(
                cmap='coolwarm',
                subset=pd.IndexSlice[['skewness'], :],
                axis=1
            )

            # 4. แสดงผล Styler ที่ปรับแต่งแล้ว
            st.dataframe(s, use_container_width=True)

            
            # Download button for stats
            csv = stats.to_csv()
            st.download_button(
                label="📥 Download Statistics as CSV",
                data=csv,
                file_name=f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with stat_tab2:
            # Distribution plots
            for var in st.session_state.selected_variables:
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=df_display[var],
                    name=var,
                    nbinsx=30,
                    opacity=0.7
                ))
                fig_dist.add_trace(go.Scatter(
                    x=df_display[var].sort_values(),
                    y=pd.Series(range(len(df_display))),
                    mode='lines',
                    name='Cumulative',
                    yaxis='y2',
                    line=dict(color='red', width=2)
                ))
                
                fig_dist.update_layout(
                    title=f"Distribution of {var.replace('_', ' ').title()}",
                    xaxis_title=var,
                    yaxis_title="Frequency",
                    yaxis2=dict(title="Cumulative %", overlaying='y', side='right'),
                    height=400,
                    showlegend=True,
                    template="plotly_white"
                )
                
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with stat_tab3:
            # Correlation heatmap
            if len(st.session_state.selected_variables) >= 2:
                corr_matrix = df_display[st.session_state.selected_variables].corr()
                
                fig_heatmap = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    color_continuous_scale='RdBu',
                    aspect='auto',
                    title="Correlation Heatmap"
                )
                
                fig_heatmap.update_layout(height=500)
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Correlation insights
                st.info("💡 **Insights:**")
                for i in range(len(corr_matrix)):
                    for j in range(i+1, len(corr_matrix)):
                        corr_val = corr_matrix.iloc[i, j]
                        var1 = corr_matrix.index[i]
                        var2 = corr_matrix.columns[j]
                        
                        if abs(corr_val) > 0.7:
                            strength = "strong" if abs(corr_val) > 0.8 else "moderate"
                            direction = "positive" if corr_val > 0 else "negative"
                            st.write(f"• {var1} and {var2}: {strength} {direction} correlation ({corr_val:.3f})")
            else:
                st.info("Select at least 2 variables to see correlation analysis")
        
        # Last update time
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"🕐 Last data point: {df_display['timestamp_local_dt'].max().strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            st.caption(f"📊 Total data points: {len(df_display):,}")

