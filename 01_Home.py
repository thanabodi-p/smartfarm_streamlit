# import streamlit as st
# import time
# from datetime import datetime
# from utils import load_data_from_mongo, calculate_vpd, get_vpd_status

# # --- 1. ตั้งค่าพื้นฐาน (ทำครั้งเดียว) ---
# st.set_page_config(page_title="Smart Framing Dashboard", layout="wide")
# st.title("🌱 SmartFarm Real-Time Dashboard")

# # --- 2. สร้างฟังก์ชันสำหรับวาด Dashboard ---
# def draw_dashboard(df_raw):
#     """
#     ฟังก์ชันนี้รับ DataFrame ดิบเข้ามา แล้ววาดส่วนแสดงผลทั้งหมด
#     """
#     if df_raw.empty:
#         st.warning("ไม่พบข้อมูลในช่วง 24 ชั่วโมงที่ผ่านมา")
#         return # ออกจากฟังก์ชันถ้าไม่มีข้อมูล

#     # --- ส่วนที่ 1: กรองข้อมูลและแสดงผลสรุป ---
#     st.subheader("ข้อมูลสรุปภาพรวม (Device: SmartFarm)")
#     df_smartfarm = df_raw[df_raw['deviceName'] == 'SmartFarm'].copy()

#     if df_smartfarm.empty:
#         st.warning("ไม่พบข้อมูลจาก Device 'SmartFarm' ในช่วง 24 ชั่วโมงที่ผ่านมา")
#         return # ออกจากฟังก์ชันถ้าไม่มีข้อมูลจาก Device นี้

#     # ดึงข้อมูลแถวล่าสุดเพื่อแสดงผลสรุป
#     latest_data = df_smartfarm.sort_values(by='timestamp_local_dt').iloc[-1]
    
#     # คำนวณ VPD ล่าสุด
#     latest_vpd = calculate_vpd(latest_data['temperature'], latest_data['humidity'])
#     vpd_status, vpd_color = get_vpd_status(latest_vpd)

#     # แบ่งคอลัมน์เพื่อแสดงผลสรุป
#     col1, col2, col3, col4 = st.columns(4)
#     col1.metric("🌡️ อุณหภูมิ", f"{latest_data['temperature']:.2f} °C")
#     col2.metric("💧 ความชื้นอากาศ", f"{latest_data['humidity']:.2f} %")
#     col3.metric("💨 VPD", f"{latest_vpd:.2f} kPa", help="Vapor Pressure Deficit: ค่าความแตกต่างระหว่างความดันไออิ่มตัวกับความดันไอในอากาศจริง ยิ่งค่าสูง อากาศยิ่งแห้ง")
#     col4.markdown(f"**สถานะ VPD:** <span style='color:{vpd_color};'>{vpd_status}</span>", unsafe_allow_html=True)

#     # --- ส่วนที่ 2: กราฟ ---
#     st.divider()
#     st.subheader("กราฟแสดงผลข้อมูลตามช่วงเวลา")
#     chart_data = df_smartfarm.rename(columns={'timestamp_local_dt': 'index'}).set_index('index')

#     st.write("##### **กราฟอุณหภูมิและความชื้นอากาศ**")
#     st.line_chart(chart_data[['temperature', 'humidity']])

#     st.write("##### **กราฟความชื้นดิน (Soil Raw)**")
#     soil_columns = ['soil_raw_1', 'soil_raw_2', 'soil_raw_3', 'soil_raw_4']
#     st.line_chart(chart_data[soil_columns])

#     st.success(f"ข้อมูลอัปเดตล่าสุดเมื่อ {datetime.now().strftime('%H:%M:%S')}")
    

# # --- 3. สร้าง Placeholder และลูป Real-time ---
# placeholder = st.empty()

# while True:
#     # ดึงข้อมูลใหม่
#     df_data = load_data_from_mongo("telemetry_data_clean", "SmartFarm")
    
#     # สั่งให้วาด Dashboard ใหม่ทั้งหมดลงใน Placeholder
#     with placeholder.container():
#         draw_dashboard(df_data)
        
#     # หน่วงเวลา 5 วินาที
#     time.sleep(5)

# pages/1_🌱_สถานะฟาร์ม.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import load_data_from_mongo, calculate_vpd, get_vpd_status
from streamlit_autorefresh import st_autorefresh

# --- Page Config ---
st.set_page_config(
    page_title="Smart Framing Dashboard",
    page_icon="🌱",
    layout="wide"
)

# --- Auto-refresh every 5 seconds ---
st_autorefresh(interval=5000, key="monitoring_refresh")

# --- Header ---
st.title("🌱 SmartFarm Real-Time Dashboard")
st.caption(f"อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")

# --- Load Data ---
@st.cache_data(ttl=5)
def load_monitoring_data():
    """โหลดข้อมูลล่าสุดสำหรับ monitoring"""
    df_sf = load_data_from_mongo("telemetry_data_clean", "SmartFarm", time_delta_days=1)
    df_rpi = load_data_from_mongo("raspberry_pi_telemetry_clean", "raspberry_pi_status", time_delta_days=1)
    return df_sf, df_rpi

df_smartfarm, df_rpi = load_monitoring_data()

# --- Section 1: SmartFarm Status Cards ---
st.subheader("🏡 สถานะ SmartFarm")

if not df_smartfarm.empty:
    latest_sf = df_smartfarm.sort_values('timestamp_local_dt').iloc[-1]
    
    # คำนวณ VPD
    vpd = calculate_vpd(latest_sf['temperature'], latest_sf['humidity'])
    vpd_status, vpd_color = get_vpd_status(vpd)
    
    # แสดงการ์ด KPI
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🌡️ อุณหภูมิ",
            f"{latest_sf['temperature']:.1f} °C",
            f"{latest_sf['temperature'] - df_smartfarm['temperature'].mean():.1f}°",
            delta_color="inverse" if latest_sf['temperature'] > 35 else "normal"
        )
    
    with col2:
        st.metric(
            "💧 ความชื้น",
            f"{latest_sf['humidity']:.1f} %",
            f"{latest_sf['humidity'] - df_smartfarm['humidity'].mean():.1f}%"
        )
    
    with col3:
        st.metric(
            "💨 VPD",
            f"{vpd:.2f} kPa",
            help="Vapor Pressure Deficit - ค่าที่เหมาะสม 0.5-1.5 kPa"
        )
    
    with col4:
        if vpd_status == "✅ เหมาะสม":
            st.success(vpd_status)
        else:
            st.warning(vpd_status)
    
    # แสดงความชื้นดิน
    with st.container():
        st.caption("🌱 ความชื้นดิน")
        soil_cols = st.columns(4)
        for i, col in enumerate(soil_cols, 1):
            with col:
                soil_val = latest_sf[f'soil_raw_{i}']
                # แปลงค่า raw เป็นเปอร์เซ็นต์ (สมมติว่า 0-1023)
                soil_pct = (soil_val / 1023) * 100
                col.metric(f"จุดที่ {i}", f"{soil_pct:.0f}%", f"{soil_val:.0f}")
else:
    st.warning("❌ ไม่พบข้อมูลจาก SmartFarm")

st.divider()

# --- Section 2: Raspberry Pi Status Cards ---
st.subheader("🖥️ สถานะ Raspberry Pi")

if not df_rpi.empty:
    latest_rpi = df_rpi.sort_values('timestamp_local_dt').iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cpu_temp = latest_rpi['cpu_temp']
        st.metric(
            "🌡️ CPU Temp",
            f"{cpu_temp:.1f} °C",
            delta_color="inverse" if cpu_temp > 70 else "normal"
        )
    
    with col2:
        cpu_usage = latest_rpi['cpu_percent']
        st.metric(
            "⚙️ CPU Usage",
            f"{cpu_usage:.1f} %",
            delta_color="inverse" if cpu_usage > 80 else "normal"
        )
    
    with col3:
        mem = latest_rpi['memory_percent']
        st.metric(
            "🧠 Memory",
            f"{mem:.1f} %",
            delta_color="inverse" if mem > 80 else "normal"
        )
    
    with col4:
        storage = latest_rpi['disk_percent']
        st.metric(
            "💽 Storage",
            f"{storage:.1f} %",
            delta_color="inverse" if storage > 90 else "normal"
        )
    
    # System Health Summary
    issues = []
    if cpu_temp > 70:
        issues.append("⚠️ CPU ร้อนเกินไป")
    if cpu_usage > 80:
        issues.append("⚠️ CPU ใช้งานสูง")
    if mem > 80:
        issues.append("⚠️ หน่วยความจำใกล้เต็ม")
    if storage > 90:
        issues.append("⚠️ พื้นที่จัดเก็บใกล้เต็ม")
    
    if issues:
        st.error(" | ".join(issues))
    else:
        st.success("✅ ระบบทำงานปกติ")
else:
    st.warning("❌ ไม่พบข้อมูลจาก Raspberry Pi")

st.divider()

# --- Section 3: Quick Trend Charts ---
st.subheader("📈 แนวโน้มล่าสุด (3 ชั่วโมงที่ผ่านมา)")

# กรองข้อมูล 3 ชั่วโมงล่าสุด
from datetime import timedelta
time_filter = datetime.now() - timedelta(hours=3)

col1, col2 = st.columns(2)

with col1:
    if not df_smartfarm.empty:
        st.caption("🌡️ อุณหภูมิและความชื้น")
        recent_sf = df_smartfarm[df_smartfarm['timestamp_local_dt'] > time_filter]
        if not recent_sf.empty:
            chart_data = recent_sf.set_index('timestamp_local_dt')[['temperature', 'humidity']]
            st.line_chart(chart_data, height=250)
        else:
            st.info("ไม่มีข้อมูลในช่วง 3 ชั่วโมงที่ผ่านมา")

with col2:
    if not df_rpi.empty:
        st.caption("🖥️ ประสิทธิภาพระบบ")
        recent_rpi = df_rpi[df_rpi['timestamp_local_dt'] > time_filter]
        if not recent_rpi.empty:
            chart_data = recent_rpi.set_index('timestamp_local_dt')[['cpu_percent', 'memory_percent']]
            st.line_chart(chart_data, height=250)
        else:
            st.info("ไม่มีข้อมูลในช่วง 3 ชั่วโมงที่ผ่านมา")

# Soil moisture trends
if not df_smartfarm.empty:
    st.caption("🌱 แนวโน้มความชื้นดิน")
    recent_sf = df_smartfarm[df_smartfarm['timestamp_local_dt'] > time_filter]
    if not recent_sf.empty:
        soil_cols = ['soil_raw_1', 'soil_raw_2', 'soil_raw_3', 'soil_raw_4']
        chart_data = recent_sf.set_index('timestamp_local_dt')[soil_cols]
        st.line_chart(chart_data, height=200)

# --- Footer ---
st.divider()
st.caption("💡 หน้านี้อัปเดตอัตโนมัติทุก 5 วินาที | ใช้หน้า 'เครื่องมือวิเคราะห์' สำหรับการวิเคราะห์เชิงลึก")