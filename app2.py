import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Stock Structure Tool", layout="centered")

st.title("📈 Stock Structure Analysis Engine")
st.write("Analyze trends and market structure phases dynamically.")

# --- Sidebar Inputs ---
st.header("Parameters")
ticker = st.text_input("Stock Ticker", value="AAPL").strip().upper()

timeframe = st.selectbox(
    "Select Timeframe",
    options=["1h", "1d", "1wk"],
    index=1,
    help="1h = 1 Hour, 1d = 1 Day, 1wk = 1 Week"
)

period = st.selectbox(
    "Select Time Period",
    options=["1mo", "3mo", "6mo", "1y", "5y"],
    index=3,
    help="How far back to look historically"
)

def find_swings(df, window=2):
    """
    Identifies Swing Highs and Swing Lows based on a rolling window.
    """
    df = df.copy()
    # Flatten columns if yfinance returns multi-index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df['Swing_High'] = np.nan
    df['Swing_Low'] = np.nan
    
    # Loop through data to find peaks and troughs
    for i in range(window, len(df) - window):
        # Current candle highs/lows
        current_high = df['High'].iloc[i]
        current_low = df['Low'].iloc[i]
        
        # Window ranges
        left_highs = df['High'].iloc[i-window:i]
        right_highs = df['High'].iloc[i+1:i+window+1]
        
        left_lows = df['Low'].iloc[i-window:i]
        right_lows = df['Low'].iloc[i+1:i+window+1]
        
        # Check for Swing High
        if current_high > max(left_highs) and current_high > max(right_highs):
            df.loc[df.index[i], 'Swing_High'] = current_high
            
        # Check for Swing Low
        if current_low < min(left_lows) and current_low < min(right_lows):
            df.loc[df.index[i], 'Swing_Low'] = current_low
            
    return df

def determine_structure(df):
    """
    Analyzes the sequence of highs and lows to determine the current trend.
    """
    # Extract historical swings chronologically
    highs = df['Swing_High'].dropna().tolist()
    lows = df['Swing_Low'].dropna().tolist()
    
    if len(highs) < 2 or len(lows) < 2:
        return "Insufficient structural data (Try a larger time period)", "N/A", "N/A"
        
    # Get the last two structural points
    last_h, prev_h = highs[-1], highs[-2]
    last_l, prev_l = lows[-1], lows[-2]
    
    # Structure Assessment Logic
    if last_h > prev_h and last_l > prev_l:
        trend = "Bullish (Higher Highs & Higher Lows)"
        phase = "Expansion / Markup"
    elif last_h < prev_h and last_l < prev_l:
        trend = "Bearish (Lower Highs & Lower Lows)"
        phase = "Distribution / Markdown"
    elif last_h > prev_h and last_l < prev_l:
        trend = "Expanding / High Volatility"
        phase = "Broadening Structure"
    else:
        trend = "Sideways / Consolidation"
        phase = "Accumulation / Squeeze"
        
    return trend, round(last_l, 2), round(last_h, 2)

# --- Analysis Execution ---
if st.button("Run Structure Analysis", type="primary"):
    if ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            try:
                # Fetch data
                df = yf.download(tickers=ticker, period=period, interval=timeframe)
                
                if df.empty:
                    st.error("No data found. Please check the ticker symbol.")
                else:
                    # Clean the data and find swings
                    df_analyzed = find_swings(df)
                    trend, support, resistance = determine_structure(df_analyzed)
                    
                    # Safe extraction of latest close price
                    if isinstance(df['Close'], pd.DataFrame):
                        latest_close = float(df['Close'].iloc[-1].iloc[0])
                    else:
                        latest_close = float(df['Close'].iloc[-1])
                    
                    # --- UI Output Display ---
                    st.markdown("---")
                    st.subheader(f"Analysis Results for {ticker}")
                    
                    # Metrics Display without Currency Symbols
                    col1, col2, col3 = st.columns(3)
                    col1.metric(label="Latest Close", value=f"{latest_close:.2f}")
                    col2.metric(label="Nearest Support", value=f"{support}")
                    col3.metric(label="Nearest Resistance", value=f"{resistance}")
                    
                    st.markdown("### Market Structure Summary")
                    st.write(f"**Current Trend:** {trend}")
                    
                    # Basic advice box based on trend
                    if "Bullish" in trend:
                        st.success("🟢 Market is structurally strong. Look for buying opportunities on pullbacks near support.")
                    elif "Bearish" in trend:
                        st.error("🔴 Market is structurally weak. Caution on long positions; resistance zones may face selling pressure.")
                    else:
                        st.warning("🟡 Market is ranging. Look for breakouts outside the identified support and resistance zones.")
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid stock ticker.")
