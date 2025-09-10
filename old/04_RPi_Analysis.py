# page 04

import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data_from_mongo

st.set_page_config(layout="wide")
st.title("🍓 Raspberry Pi Health Monitoring")

# --- 1. โหลดข้อมูล ---
# เรียกใช้ฟังก์ชันเดิม แต่ระบุ collection และ device ใหม่
df = load_data_from_mongo(
    collection_name="raspberry_pi_telemetry_clean",
    device_name="raspberry_pi_status"
)

if df.empty:
    st.warning("ไม่พบข้อมูล Telemetry ของ Raspberry Pi")
else:
    # --- 2. ส่วนแสดงสถานะปัจจุบัน (Current Status) ---
    st.subheader("สถานะล่าสุด (Latest Status)")
    latest_data = df.sort_values(by='timestamp_local_dt').iloc[-1]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🌡️ CPU Temperature", f"{latest_data['cpu_temp']:.1f} °C")
    col2.metric("⚙️ CPU Usage", f"{latest_data['cpu_percent']:.1f} %")
    col3.metric("🧠 Memory In Use", f"{latest_data['memory_percent']:.1f} %")
    col4.metric("💽 Storage", f"{latest_data['disk_percent']:.1f} %")
    col5.metric("🌐 Net Latency", f"{latest_data['network_latency_ms']:.1f} ms")

    # --- สรุปสถานะล่าสุดแบบอัจฉริยะ ---
    summary = []
    if latest_data['cpu_temp'] > 70:
        summary.append("⚠️ CPU ร้อนเกินไป ควรตรวจสอบระบบระบายความร้อน")
    if latest_data['cpu_percent'] > 90:
        summary.append("⚠️ CPU ใช้งานสูง อาจมีโปรเซสหนัก")
    if latest_data['memory_percent'] > 90:
        summary.append("⚠️ หน่วยความจำใกล้เต็ม")
    if latest_data['disk_percent'] > 90:
        summary.append("⚠️ พื้นที่จัดเก็บใกล้เต็ม")
    if latest_data['network_latency_ms'] > 200:
        summary.append("⚠️ เครือข่ายช้า อาจมีปัญหาอินเทอร์เน็ต")

    if summary:
        st.error(" ".join(summary))
    else:
        st.success("สถานะล่าสุดอยู่ในเกณฑ์ปกติ 👍")

    # --- 3. ส่วนวิเคราะห์แนวโน้ม (Historical Trends) ---
    st.divider()
    st.subheader("กราฟแนวโน้มย้อนหลัง (Historical Trends)")
    
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    
    selected_metric = st.selectbox(
        "เลือกค่าที่ต้องการดูแนวโน้ม:",
        options=numeric_columns,
        index=numeric_columns.index('cpu_temp') # ค่าเริ่มต้น
    )
    
    fig_trend = px.line(df, x='timestamp_local_dt', y=selected_metric, title=f"แนวโน้มของ {selected_metric} ตามช่วงเวลา")
    st.plotly_chart(fig_trend, use_container_width=True)

    # --- 4. ส่วนวิเคราะห์ความสัมพันธ์ (Correlation Analysis) ---
    st.divider()
    st.subheader("ความสัมพันธ์ระหว่างตัวแปร (Correlation Heatmap)")
    st.info("ตารางนี้แสดงให้เห็นว่าตัวแปรต่างๆ มีความสัมพันธ์กันมากน้อยแค่ไหน (ค่าเข้าใกล้ 1 คือสัมพันธ์กันมาก, เข้าใกล้ 0 คือไม่สัมพันธ์กัน)")
    
    # เลือกเฉพาะคอลัมน์ที่น่าสนใจ
    corr_columns = ['cpu_percent', 'cpu_temp', 'memory_percent', 'network_latency_ms']
    corr_matrix = df[corr_columns].corr()
    
    fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
    st.plotly_chart(fig_corr, use_container_width=True)

    # --- 5. ส่วนวิเคราะห์การกระจายตัว (Distribution) ---
    st.divider()
    st.subheader("การกระจายตัวของข้อมูล (Histogram)")
    
    selected_dist_metric = st.selectbox(
        "เลือกค่าที่ต้องการดูการกระจายตัว:",
        options=numeric_columns,
        index=numeric_columns.index('network_latency_ms') # ค่าเริ่มต้น
    )
    
    fig_dist = px.histogram(df, x=selected_dist_metric, title=f"การกระจายตัวของค่า {selected_dist_metric}", marginal="box")
    st.plotly_chart(fig_dist, use_container_width=True)