import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import urllib.request
import json
from datetime import datetime

st.set_page_config(layout="wide")
st.title("🇮🇳 Institutional Price Action Tool")

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.header("Tool Configurations")
ticker = st.sidebar.text_input("Stock Ticker (e.g. RELIANCE, TCS, SBIN)", value="RELIANCE").upper().strip()
timeframe = st.sidebar.selectbox("Select Timeframe", options=["Daily", "Weekly"], index=0)
volume_multiplier = st.sidebar.slider("Volume Breakout Multiplier", min_value=1.0, max_value=3.0, value=1.5, step=0.1)

@st.cache_data(ttl=600)
def fetch_nse_data(symbol):
    try:
        # Pull clean daily/weekly intervals via open web APIs
        url = f"https://query1.financeapi.com/v8/finance/chart/{symbol}.NS?range=1y&interval=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        indicators = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'Open': indicators['open'],
            'High': indicators['high'],
            'Low': indicators['low'],
            'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s'))
        
        return df.dropna()
    except Exception as e:
        return pd.DataFrame()

df = fetch_nse_data(ticker)

if df.empty:
    st.error(f"Could not retrieve market data for '{ticker}'. Please ensure it's a valid NSE stock token.")
else:
    # Resample to weekly format if specified by user
    if timeframe == "Weekly":
        df = df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

    # ==========================================
    # 1. MARKET STRUCTURE ANALYSIS
    # ==========================================
    window = 5
    df['Swing_High'] = df['High'][(df['High'] == df['High'].rolling(window=window*2+1, center=True).max())]
    df['Swing_Low'] = df['Low'][(df['Low'] == df['Low'].rolling(window=window*2+1, center=True).min())]

    df['Last_SH'] = df['Swing_High'].ffill()
    df['Last_SL'] = df['Swing_Low'].ffill()

    current_close = df['Close'].iloc[-1]
    last_sh = df['Last_SH'].dropna().iloc[-1] if not df['Last_SH'].dropna().empty else float('inf')
    last_sl = df['Last_SL'].dropna().iloc[-1] if not df['Last_SL'].dropna().empty else float('-inf')

    structure_trend = "Sideways"
    if current_close > last_sh:
        structure_trend = "Bullish (MSS)"
    elif current_close < last_sl:
        structure_trend = "Bearish (MSS)"

    # ==========================================
    # 2. SUPPORT & RESISTANCE (Rule A, B, C, D)
    # ==========================================
    all_levels = pd.concat([df['Swing_High'].dropna(), df['Swing_Low'].dropna()]).tolist()

    closest_sup = None
    closest_res = None
    min_sup_diff = float('inf')
    min_res_diff = float('inf')

    for level in all_levels:
        if level < current_close and (current_close - level) < min_sup_diff:
            min_sup_diff = current_close - level
            closest_sup = level
        elif level > current_close and (level - current_close) < min_res_diff:
            min_res_diff = level - current_close
            closest_res = level

    # ==========================================
    # 3. BREAKOUT OR BREAKDOWN
    # ==========================================
    df['Vol_MA'] = df['Volume'].rolling(window=20).mean()
    df['High_Vol'] = df['Volume'] > (df['Vol_MA'] * volume_multiplier)

    df['Breakout'] = False
    df['Breakdown'] = False

    if closest_res:
        df['Breakout'] = (df['Close'] > closest_res) & (df['Close'].shift(1) <= closest_res) & df['High_Vol']
    if closest_sup:
        df['Breakdown'] = (df['Close'] < closest_sup) & (df['Close'].shift(1) >= closest_sup) & df['High_Vol']

    # ==========================================
    # 4. PRICE REJECT CANDLESTICK PATTERNS
    # ==========================================
    body = (df['Close'] - df['Open']).abs()
    upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
    lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']

    df['Hammer'] = (lower_shadow > (body * 2)) & (upper_shadow < (body * 0.5)) & (df['Low'] <= closest_sup * 1.002 if closest_sup else False)
    df['Shooting_Star'] = (upper_shadow > (body * 2)) & (lower_shadow < (body * 0.5)) & (df['High'] >= closest_res * 0.998 if closest_res else False)

    # ==========================================
    # 5. CHART VISUALIZATION
    # ==========================================
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Price Action"
    ))

    if closest_res:
        fig.add_shape(type="line", x0=df.index[0], y0=closest_res, x1=df.index[-1], y1=closest_res,
                      line=dict(color="Red", width=2, dash="dash"), name="Near Resistance")
    if closest_sup:
        fig.add_shape(type="line", x0=df.index[0], y0=closest_sup, x1=df.index[-1], y1=closest_sup,
                      line=dict(color="Green", width=2, dash="dash"), name="Near Support")

    # Plot Signals
    breakouts = df[df['Breakout']]
    fig.add_trace(go.Scatter(x=breakouts.index, y=breakouts['Low'] * 0.99, mode='markers',
                             marker=dict(symbol='triangle-up', size=14, color='lime'), name='Institutional Breakout'))

    breakdowns = df[df['Breakdown']]
    fig.add_trace(go.Scatter(x=breakdowns.index, y=breakdowns['High'] * 1.01, mode='markers',
                             marker=dict(symbol='triangle-down', size=14, color='red'), name='Institutional Breakdown'))

    hammers = df[df['Hammer']]
    fig.add_trace(go.Scatter(x=hammers.index, y=hammers['Low'] * 0.98, mode='markers',
                             marker=dict(symbol='circle', size=10, color='cyan'), name='Hammer Rejection'))

    stars = df[df['Shooting_Star']]
    fig.add_trace(go.Scatter(x=stars.index, y=stars['High'] * 1.02, mode='markers',
                             marker=dict(symbol='circle', size=10, color='orange'), name='Shooting Star Rejection'))

    fig.update_layout(
        title=f"{ticker} | Current Trend Bias: {structure_trend}",
        yaxis_title="Price (INR)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=650
    )

    st.plotly_chart(fig, use_container_width=True)
