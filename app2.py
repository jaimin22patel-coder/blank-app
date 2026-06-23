import streamlit as st
import pandas as pd
import numpy as np
from tvdatafeed import TvDatafeed, Interval

# Initialize TradingView Datafeed
@st.cache_resource
def init_tv():
    # Anonymous login; replace with username/password if you have a premium TV account
    return TvDatafeed()

tv = init_tv()

# --- 1. UI INPUT & CONFIGURATION ---
st.title("🇮🇳 Indian Stock Price Action Analysis Tool")
st.sidebar.header("Control Panel")

# Timeframe Dropdown
tf_choice = st.sidebar.selectbox(
    "Select Timeframe",
    options=["1m", "5m", "15m", "1H", "4H", "1D"],
    index=3 # Default to 1H
)

# Map UI selection to TradingView intervals
tf_map = {
    "1m": Interval.in_1minute,
    "5m": Interval.in_5minute,
    "15m": Interval.in_15minute,
    "1H": Interval.in_1hour,
    "4H": Interval.in_4hour,
    "1D": Interval.in_daily
}

# Lookback Period Dropdown (Translated to number of candles to fetch)
lookback_choice = st.sidebar.selectbox(
    "Select Lookback Period",
    options=["50 Candles", "100 Candles", "250 Candles", "500 Candles"],
    index=2 # Default to 250
)
n_candles = int(lookback_choice.split()[0])

# Stock Symbol Input
symbol = st.sidebar.text_input("Enter NSE Stock Symbol (e.g., RELIANCE, SBIN)", value="RELIANCE").upper()

# --- DATA FETCHING ---
@st.cache_data(ttl=60) # Cache for 1 minute to prevent constant API spamming
def load_data(sym, tf, length):
    try:
        df = tv.get_hist(symbol=sym, exchange='NSE', interval=tf_map[tf], n_bars=length)
        if df is not None and not df.empty:
            df = df.reset_index()
            # Ensure standard column names
            df.columns = [c.lower() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
    return None

df = load_data(symbol, tf_choice, n_candles)

if df is not None:
    cmp = df['close'].iloc[-1]
    st.metric(label=f"Current Market Price (CMP) - NSE:{symbol}", value=f"₹{cmp:.2f}")

    # --- 2. LOGIC: SWING HIGHS & LOWS (Market Structure) ---
    window = 5
    df['is_high'] = (df['high'] == df['high'].rolling(window=window*2+1, center=True).max())
    df['is_low'] = (df['low'] == df['low'].rolling(window=window*2+1, center=True).min())

    # --- 3. LOGIC: SUPPORT & RESISTANCE (Rule d: Chart-Based Proximity) ---
    swing_highs = df[df['is_high']]['high'].tolist()
    swing_lows = df[df['is_low']]['low'].tolist()
    
    # Chart-based boundary: Find the immediate closest structural points above and below CMP
    upper_bounds = [h for h in swing_highs if h > cmp]
    lower_bounds = [l for l in swing_lows if l < cmp]
    
    nearest_resistance_ceiling = min(upper_bounds) if upper_bounds else df['high'].max()
    nearest_support_floor = max(lower_bounds) if lower_bounds else df['low'].min()

    # Filter all historical levels to strictly fit within our chart room boundaries (Rule D)
    valid_resistances = [h for h in swing_highs if cmp < h <= nearest_resistance_ceiling]
    valid_supports = [l for l in swing_lows if nearest_support_floor <= l < cmp]

    # --- 4. LOGIC: CANDLESTICK PATTERNS ---
    # Helper to calculate candle dimensions
    body = (df['close'] - df['open']).abs()
    candle_range = df['high'] - df['low']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    
    # Identify Hammer & Shooting Star
    df['hammer'] = (lower_wick > (2 * body)) & (upper_wick < (0.2 * candle_range)) & (body > 0)
    df['shooting_star'] = (upper_wick > (2 * body)) & (lower_wick < (0.2 * candle_range)) & (body > 0)
    
    # Identify Engulfing Patterns
    df['bullish_engulfing'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                              (df['close'] > df['open']) & \
                              (df['close'] >= df['open'].shift(1)) & \
                              (df['open'] <= df['close'].shift(1))
                              
    df['bearish_engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                              (df['close'] < df['open']) & \
                              (df['close'] <= df['open'].shift(1)) & \
                              (df['open'] >= df['close'].shift(1))

    # --- 5. LOGIC: BREAKOUT / BREAKDOWN WITH VOLUME ---
    vol_ma = df['volume'].rolling(window=20).mean()
    df['high_vol'] = df['volume'] > (1.5 * vol_ma) # 1.5x average volume
    
    # Check last few bars for breakout/breakdown
    latest_bar = df.iloc[-1]
    prev_bar = df.iloc[-2]
    
    breakout_triggered = prev_bar['close'] > nearest_resistance_ceiling and prev_bar['high_vol']
    breakdown_triggered = prev_bar['close'] < nearest_support_floor and prev_bar['high_vol']

    # --- DISPLAY ANALYTICS RESULTS ---
    
    st.subheader("1. Market Structure & Trend")
    # Quick simple trend logic based on last 2 structural points
    last_highs = df[df['is_high']]['high'].tail(2).tolist()
    if len(last_highs) == 2:
        if last_highs[1] > last_highs[0]:
            st.success("Structure: Bullish (Making Higher Highs)")
        else:
            st.color_picker("Structure: Bearish (Making Lower Highs)", "#FF4B4B")
    else:
        st.info("Structure: Consolidating / Insufficient structural pivots.")

    st.subheader("2. Chart-Based Proximity Levels")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Nearest Support Floor", value=f"₹{nearest_support_floor:.2f}")
    with col2:
        st.metric(label="Nearest Resistance Ceiling", value=f"₹{nearest_resistance_ceiling:.2f}")

    st.subheader("3. Breakout & Volume Scan")
    if breakout_triggered:
        st.success(f"⚠️ BULLISH BREAKOUT CONFIRMED: Price broke above ₹{nearest_resistance_ceiling:.2f} with High Volume. Watch for a Retest.")
    elif breakdown_triggered:
        st.error(f"⚠️ BEARISH BREAKDOWN CONFIRMED: Price cracked below ₹{nearest_support_floor:.2f} with High Volume. Watch for a Retest.")
    else:
        st.write("No active structural breakouts matching volume parameters right now.")

    st.subheader("4. Price Action Rejection / Hold Scan (Current Candles)")
    patterns_found = []
    if latest_bar['hammer']: patterns_found.append("🔨 Hammer Found (Potential Institutional Support Hold)")
    if latest_bar['bullish_engulfing']: patterns_found.append("📈 Bullish Engulfing Pattern")
    if latest_bar['shooting_star']: patterns_found.append("💫 Shooting Star Found (Potential Institutional Rejection)")
    if latest_bar['bearish_engulfing']: patterns_found.append("📉 Bearish Engulfing Pattern")
    
    if patterns_found:
        for p in patterns_found:
            st.info(p)
    else:
        st.write("No institutional rejection patterns printing on the immediate candle.")

else:
    st.warning("Please enter a valid NSE stock ticker and ensure you have internet connectivity to load TradingView charts.")
