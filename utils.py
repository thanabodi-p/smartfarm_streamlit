import streamlit as st
import pandas as pd
import pymongo
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from io import BytesIO

# ข้อมูลการเชื่อมต่อ MongoDB
# PASSWORD = quote_plus("@mwte@mp@55")
# MONGO_URI = f"mongodb://admin:{PASSWORD}@191.20.110.47:27019/?authSource=admin"
MONGO_USER = st.secrets["db_username"]
MONGO_PASSWORD = st.secrets["db_password"]
MONGO_HOST = st.secrets["db_host"]
MONGO_URI = f"mongodb://{MONGO_USER}:{quote_plus(MONGO_PASSWORD)}@{MONGO_HOST}:27019/?authSource=admin"
MONGO_DB_NAME = "Smart_Framing_Db"
MONGO_COLLECTION_NAME = "telemetry_data_clean"

# --- 1. ฟังก์ชันคำนวณที่เกี่ยวข้องกับการเกษตร ---

def calculate_vpd(temperature: float, humidity: float) -> float:
    """
    คำนวณค่า Vapor Pressure Deficit (VPD) ในหน่วย kPa
    
    Args:
        temperature: อุณหภูมิในหน่วย °C
        humidity: ความชื้นสัมพัทธ์ในหน่วย %
    
    Returns:
        ค่า VPD ในหน่วย kPa
    """
    svp = 0.61078 * math.exp((17.27 * temperature) / (temperature + 237.3))
    avp = svp * (humidity / 100)
    vpd = svp - avp
    return vpd

def get_vpd_status(vpd: float) -> Tuple[str, str]:
    """
    ประเมินสถานะของค่า VPD และคืนค่าเป็นข้อความและสี
    
    Args:
        vpd: ค่า VPD ในหน่วย kPa
    
    Returns:
        Tuple ของ (ข้อความสถานะ, สีสำหรับแสดงผล)
    """
    if 0.5 <= vpd <= 1.5:
        return "✅ เหมาะสม", "green"
    elif vpd < 0.5:
        return "⚠️ ไม่เหมาะสม (อากาศชื้นเกินไป)", "orange"
    else:  # vpd > 1.5
        return "⚠️ ไม่เหมาะสม (อากาศแห้งเกินไป)", "red"

def calculate_dew_point(temperature: float, humidity: float) -> float:
    """
    คำนวณจุดน้ำค้าง (Dew Point)
    
    Args:
        temperature: อุณหภูมิในหน่วย °C
        humidity: ความชื้นสัมพัทธ์ในหน่วย %
    
    Returns:
        จุดน้ำค้างในหน่วย °C
    """
    a = 17.27
    b = 237.7
    alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    return dew_point

def calculate_heat_index(temperature: float, humidity: float) -> float:
    """
    คำนวณดัชนีความร้อน (Heat Index)
    
    Args:
        temperature: อุณหภูมิในหน่วย °C
        humidity: ความชื้นสัมพัทธ์ในหน่วย %
    
    Returns:
        ดัชนีความร้อนในหน่วย °C
    """
    # Convert to Fahrenheit for calculation
    T = temperature * 9/5 + 32
    RH = humidity
    
    # Simple formula
    HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH - 0.00683783*T*T - 0.05481717*RH*RH + 0.00122874*T*T*RH + 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
    
    # Convert back to Celsius
    return (HI - 32) * 5/9

# --- 2. ฟังก์ชันหลักสำหรับดึงและประมวลผลข้อมูล ---

@st.cache_data(ttl=300)
def load_data_from_mongo(
    collection_name: str, 
    device_name: str, 
    time_delta_days: int = 1,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    ดึงข้อมูลจาก MongoDB และแปลงเป็น DataFrame
    
    Args:
        collection_name: ชื่อ collection ใน MongoDB
        device_name: ชื่ออุปกรณ์ที่ต้องการดึงข้อมูล
        time_delta_days: จำนวนวันย้อนหลังที่ต้องการดึงข้อมูล (ถ้าไม่ระบุ start_date/end_date)
        start_date: วันเริ่มต้น (optional)
        end_date: วันสิ้นสุด (optional)
    
    Returns:
        DataFrame ที่มีข้อมูลจาก MongoDB
    """
    mongo_client = None
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client[MONGO_DB_NAME]
        collection = db[collection_name]
        
        utc_offset = timedelta(hours=7)
        
        # กำหนดช่วงเวลา
        if start_date and end_date:
            start_date_utc = start_date - utc_offset
            end_date_utc = end_date - utc_offset
        else:
            end_date_utc = datetime.utcnow()
            start_date_utc = end_date_utc - timedelta(days=time_delta_days)
        
        query = {
            "deviceName": device_name,
            "timestamp_utc": {
                "$gte": start_date_utc.strftime('%Y-%m-%dT%H:%M:%S'),
                "$lt": end_date_utc.strftime('%Y-%m-%dT%H:%M:%S')
            }
        }

        documents = list(collection.find(query).sort("_id", -1))
        
        if not documents:
            return pd.DataFrame()

        df = pd.DataFrame(documents)
        df['timestamp_utc_dt'] = pd.to_datetime(df['timestamp_utc'])
        df['timestamp_local_dt'] = df['timestamp_utc_dt'] + utc_offset
        
        return df
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลจาก {collection_name}: {e}")
        return pd.DataFrame()
    finally:
        if mongo_client:
            mongo_client.close()

# --- 3. ฟังก์ชันสำหรับการวิเคราะห์ข้อมูล ---

def calculate_statistics(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    คำนวณสถิติเชิงลึกสำหรับคอลัมน์ที่เลือก
    
    Args:
        df: DataFrame ที่ต้องการวิเคราะห์
        columns: รายชื่อคอลัมน์ที่ต้องการวิเคราะห์
    
    Returns:
        DataFrame ที่มีค่าสถิติ
    """
    stats = df[columns].describe()
    
    # เพิ่มสถิติเพิ่มเติม
    stats.loc['variance'] = df[columns].var()
    stats.loc['skewness'] = df[columns].skew()
    stats.loc['kurtosis'] = df[columns].kurtosis()
    stats.loc['cv'] = (df[columns].std() / df[columns].mean()) * 100  # Coefficient of Variation
    
    return stats

def detect_anomalies(df: pd.DataFrame, column: str, method: str = 'iqr', threshold: float = 1.5) -> pd.Series:
    """
    ตรวจจับค่าผิดปกติในข้อมูล
    
    Args:
        df: DataFrame ที่ต้องการวิเคราะห์
        column: คอลัมน์ที่ต้องการตรวจสอบ
        method: วิธีการตรวจจับ ('iqr', 'zscore', 'isolation_forest')
        threshold: ค่า threshold สำหรับการตรวจจับ
    
    Returns:
        Series ของ boolean ที่บอกว่าแต่ละแถวเป็นค่าผิดปกติหรือไม่
    """
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (df[column] < lower_bound) | (df[column] > upper_bound)
    
    elif method == 'zscore':
        z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
        return z_scores > threshold
    
    else:
        # Default to IQR if method not recognized
        return detect_anomalies(df, column, 'iqr', threshold)

def calculate_moving_averages(df: pd.DataFrame, column: str, windows: List[int] = [5, 10, 20]) -> pd.DataFrame:
    """
    คำนวณค่าเฉลี่ยเคลื่อนที่สำหรับหลายๆ window
    
    Args:
        df: DataFrame ที่ต้องการวิเคราะห์
        column: คอลัมน์ที่ต้องการคำนวณ
        windows: รายการของขนาด window ที่ต้องการ
    
    Returns:
        DataFrame ที่มีค่าเฉลี่ยเคลื่อนที่
    """
    result = df.copy()
    for window in windows:
        result[f'{column}_ma{window}'] = df[column].rolling(window=window, min_periods=1).mean()
    return result

def calculate_rate_of_change(df: pd.DataFrame, column: str, period: int = 1) -> pd.Series:
    """
    คำนวณอัตราการเปลี่ยนแปลงของข้อมูล
    
    Args:
        df: DataFrame ที่ต้องการวิเคราะห์
        column: คอลัมน์ที่ต้องการคำนวณ
        period: ช่วงเวลาสำหรับการคำนวณ
    
    Returns:
        Series ของอัตราการเปลี่ยนแปลง
    """
    return df[column].diff(period) / df[column].shift(period) * 100

# --- 4. ฟังก์ชันสำหรับการจัดรูปแบบข้อมูล ---

def format_dataframe_for_display(df: pd.DataFrame, decimal_places: int = 2) -> pd.DataFrame:
    """
    จัดรูปแบบ DataFrame สำหรับการแสดงผล
    
    Args:
        df: DataFrame ที่ต้องการจัดรูปแบบ
        decimal_places: จำนวนทศนิยมที่ต้องการแสดง
    
    Returns:
        DataFrame ที่จัดรูปแบบแล้ว
    """
    styled_df = df.style.format(f"{{:.{decimal_places}f}}")
    return styled_df

def create_time_bins(df: pd.DataFrame, time_column: str = 'timestamp_local_dt') -> pd.DataFrame:
    """
    สร้าง bins สำหรับการวิเคราะห์ตามช่วงเวลา
    
    Args:
        df: DataFrame ที่ต้องการวิเคราะห์
        time_column: ชื่อคอลัมน์ที่เก็บข้อมูลเวลา
    
    Returns:
        DataFrame ที่มีคอลัมน์ช่วงเวลาเพิ่มเติม
    """
    result = df.copy()
    result['hour'] = pd.to_datetime(result[time_column]).dt.hour
    result['day_of_week'] = pd.to_datetime(result[time_column]).dt.dayofweek
    result['day_name'] = pd.to_datetime(result[time_column]).dt.day_name()
    result['is_weekend'] = result['day_of_week'].isin([5, 6])
    
    # Time period classification
    result['time_period'] = result['hour'].apply(
        lambda x: 'Morning' if 6 <= x < 12 else
                  'Afternoon' if 12 <= x < 18 else
                  'Evening' if 18 <= x < 24 else 'Night'
    )
    
    return result

# --- 5. ฟังก์ชันสำหรับ Alert และ Notification ---

def check_thresholds(
    value: float, 
    thresholds: Dict[str, Tuple[float, float]], 
    parameter_name: str
) -> Tuple[str, str]:
    """
    ตรวจสอบค่าเทียบกับ thresholds ที่กำหนด
    
    Args:
        value: ค่าที่ต้องการตรวจสอบ
        thresholds: Dictionary ของ thresholds {'normal': (min, max), 'warning': (min, max)}
        parameter_name: ชื่อพารามิเตอร์
    
    Returns:
        Tuple ของ (สถานะ, ข้อความ)
    """
    if 'critical' in thresholds:
        min_crit, max_crit = thresholds['critical']
        if value < min_crit or value > max_crit:
            return 'critical', f"🚨 {parameter_name} อยู่ในระดับวิกฤต!"
    
    if 'warning' in thresholds:
        min_warn, max_warn = thresholds['warning']
        if value < min_warn or value > max_warn:
            return 'warning', f"⚠️ {parameter_name} อยู่ในระดับเฝ้าระวัง"
    
    if 'normal' in thresholds:
        min_norm, max_norm = thresholds['normal']
        if min_norm <= value <= max_norm:
            return 'normal', f"✅ {parameter_name} อยู่ในระดับปกติ"
    
    return 'unknown', f"❓ {parameter_name} ไม่สามารถประเมินได้"

def prepare_export_data(df: pd.DataFrame, format_type: str = 'csv') -> bytes:
    """
    เตรียมข้อมูล DataFrame ให้อยู่ในรูปแบบ bytes สำหรับปุ่ม Download ของ Streamlit
    รองรับ Format 'csv' และ 'excel'

    Args:
        df: DataFrame ที่ต้องการ export
        format_type: ประเภทของไฟล์ ('csv' หรือ 'excel')

    Returns:
        ข้อมูลในรูปแบบ bytes
    """
    if format_type == 'csv':
        # แปลงเป็น CSV และเข้ารหัสเป็น utf-8
        return df.to_csv(index=False).encode('utf-8')
        
    elif format_type == 'excel':
        # ใช้ BytesIO เพื่อสร้างไฟล์ Excel ในหน่วยความจำ
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='data_export')
        # ดึงข้อมูล bytes จาก buffer
        return output_buffer.getvalue()
        
    else:
        raise ValueError(f"Unsupported export format: '{format_type}'. Please use 'csv' or 'excel'.")
