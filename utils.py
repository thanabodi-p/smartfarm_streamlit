import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from io import BytesIO

# --- Constants ---
# This is the address of your API server.
API_BASE_URL = "https://smartfarm-api-peer.onrender.com"

# --- 1. NEW Data Loading Function (Replaces the old MongoDB connection) ---
@st.cache_data(ttl=60)
def load_data_from_api(source: str) -> pd.DataFrame:
    """
    Fetches data for the last 7 days from our new API server.
    """
    endpoint_map = {
        "SmartFarm": "/data/smartfarm",
        "Raspberry Pi": "/data/raspberrypi"
    }
    endpoint = endpoint_map.get(source)

    if not endpoint:
        st.error(f"Unknown data source: {source}")
        return pd.DataFrame()

    try:
        full_url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        if not df.empty:
            if 'timestamp_utc' in df.columns:
                df['timestamp_utc_dt'] = pd.to_datetime(df['timestamp_utc'])
            if 'timestamp_local' in df.columns:
                df['timestamp_local_dt'] = pd.to_datetime(df['timestamp_local'])
            if 'timestamp_local_dt' not in df.columns and 'timestamp_utc_dt' in df.columns:
                 df['timestamp_local_dt'] = df['timestamp_utc_dt'] + timedelta(hours=7)
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Could not connect to API Server at {API_BASE_URL}. Is it running? Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while fetching data from the API: {e}")
        return pd.DataFrame()

# --- 2. Agricultural Calculation Functions (Kept from your original file) ---

def calculate_vpd(temperature: float, humidity: float) -> float:
    if pd.isna(temperature) or pd.isna(humidity): return 0.0
    svp = 0.61078 * math.exp((17.27 * temperature) / (temperature + 237.3))
    avp = svp * (humidity / 100)
    return svp - avp

def get_vpd_status(vpd: float) -> Tuple[str, str]:
    if 0.5 <= vpd <= 1.5:
        return "✅ เหมาะสม", "green"
    elif vpd < 0.5:
        return "⚠️ ไม่เหมาะสม (อากาศชื้นเกินไป)", "orange"
    else:
        return "⚠️ ไม่เหมาะสม (อากาศแห้งเกินไป)", "red"

def calculate_dew_point(temperature: float, humidity: float) -> float:
    a = 17.27
    b = 237.7
    alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)
    return (b * alpha) / (a - alpha)

def calculate_heat_index(temperature: float, humidity: float) -> float:
    T = temperature * 9/5 + 32
    RH = humidity
    HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH - 0.00683783*T*T - 0.05481717*RH*RH + 0.00122874*T*T*RH + 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
    return (HI - 32) * 5/9

# --- 3. Data Analysis Functions (Kept from your original file) ---

def calculate_statistics(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    existing_cols = [col for col in columns if col in df.columns]
    if not existing_cols: return pd.DataFrame()
    stats = df[existing_cols].describe()
    stats.loc['variance'] = df[existing_cols].var()
    stats.loc['skewness'] = df[existing_cols].skew()
    stats.loc['kurtosis'] = df[existing_cols].kurtosis()
    stats.loc['cv'] = (df[existing_cols].std() / df[existing_cols].mean()) * 100
    return stats

def detect_anomalies(df: pd.DataFrame, column: str, method: str = 'iqr', threshold: float = 1.5) -> pd.Series:
    if method == 'iqr':
        Q1, Q3 = df[column].quantile(0.25), df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound, upper_bound = Q1 - threshold * IQR, Q3 + threshold * IQR
        return (df[column] < lower_bound) | (df[column] > upper_bound)
    elif method == 'zscore':
        z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
        return z_scores > threshold
    return pd.Series([False] * len(df))

def calculate_moving_averages(df: pd.DataFrame, column: str, windows: List[int] = [5, 10, 20]) -> pd.DataFrame:
    result = df.copy()
    for window in windows:
        result[f'{column}_ma{window}'] = df[column].rolling(window=window, min_periods=1).mean()
    return result

def calculate_rate_of_change(df: pd.DataFrame, column: str, period: int = 1) -> pd.Series:
    return df[column].diff(period) / df[column].shift(period) * 100

# --- 4. Formatting and Helper Functions (Kept from your original file) ---

def create_time_bins(df: pd.DataFrame, time_column: str = 'timestamp_local_dt') -> pd.DataFrame:
    result = df.copy()
    dt_series = pd.to_datetime(result[time_column])
    result['hour'] = dt_series.dt.hour
    result['day_name'] = dt_series.dt.day_name()
    result['time_period'] = result['hour'].apply(lambda x: 'Morning' if 6<=x<12 else 'Afternoon' if 12<=x<18 else 'Evening' if 18<=x<24 else 'Night')
    return result

def check_thresholds(value: float, thresholds: Dict[str, Tuple[float, float]], parameter_name: str) -> Tuple[str, str]:
    if 'critical' in thresholds and (value < thresholds['critical'][0] or value > thresholds['critical'][1]):
        return 'critical', f"🚨 {parameter_name} is at a critical level!"
    if 'warning' in thresholds and (value < thresholds['warning'][0] or value > thresholds['warning'][1]):
        return 'warning', f"⚠️ {parameter_name} is at a warning level."
    if 'normal' in thresholds and (thresholds['normal'][0] <= value <= thresholds['normal'][1]):
        return 'normal', f"✅ {parameter_name} is at a normal level."
    return 'unknown', f"❓ Cannot assess {parameter_name}."

def prepare_export_data(df: pd.DataFrame, format_type: str = 'csv') -> bytes:
    if format_type == 'csv':
        return df.to_csv(index=False).encode('utf-8')
    elif format_type == 'excel':
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='data_export')
        return output_buffer.getvalue()
    raise ValueError("Unsupported format. Please use 'csv' or 'excel'.")

