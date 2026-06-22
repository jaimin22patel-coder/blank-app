import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Price Action Automation Engine", layout="centered")
st.title("🤖 Automated Price Action Engine")
st.write("Analysis based purely on market structure, S&R zones, and price dynamics.")

# --- CORE ALGORITHM FUNCTIONS ---
def fetch_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y", interval="1d")
    if df.empty:
        return None
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

def analyze_market_structure(df, window=20):
    long_term_df = df.iloc[-250:].copy()
    long_term_df['Peak'] = long_term_df['High'].rolling(window=window, center=True).max()
    long_term_df['Trough'] = long_term_df['Low'].rolling(window=window, center=True).min()
    
    highs = long_term_df.dropna(subset=['Peak'])['High'].drop_duplicates().tolist()[-3:]
    lows = long_term_df.dropna(subset=['Trough'])['Low'].drop_duplicates().tolist()[-3:]
    
    if len(highs) < 2 or len(lows) < 2:
        return "Sideways / Undefined"
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "Bullish (Uptrend)"
    elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "Bearish (Downtrend)"
    else:
        return "Sideways / Consolidation"

def find_sr_zones(df, current_price, window=15, proximity_pct=0.10, cluster_pct=0.015):
    long_term_df = df.iloc[-250:].copy()
    raw_levels = []
    for i in range(window, len(long_term_df) - window):
        if long_term_df['Low'].iloc[i] == long_term_df['Low'].iloc[i-window:i+window+1].min():
            raw_levels.append(long_term_df['Low'].iloc[i])
        if long_term_df['High'].iloc[i] == long_term_df['High'].iloc[i-window:i+window+1].max():
            raw_levels.append(long_term_df['High'].iloc[i])
            
    valid_levels = [lvl for lvl in raw_levels if abs(lvl - current_price) / current_price <= proximity_pct]
    valid_levels.sort()
    
    zones = []
    if not valid_levels:
        return zones
        
    current_zone = [valid_levels[0]]
    for lvl in valid_levels[1:]:
        if (lvl - current_zone[-1]) / current_zone[-1] <= cluster_pct:
            current_zone.append(lvl)
        else:
            zones.append(np.mean(current_zone))
            current_zone = [lvl]
    zones.append(np.mean(current_zone))
    return sorted(list(set(zones)))

def check_price_dynamics(short_term_df, zones):
    last_5_days = short_term_df.tail(5)
    dynamic_status = "No active zone setup"
    matched_zone = None
    setup_type = None

    for zone in zones:
        zone_upper = zone * 1.01
        zone_lower = zone * 0.99
        for idx, row in last_5_days.iterrows():
            candle_body = abs(row['Close'] - row['Open'])
            total_range = row['High'] - row['Low']
            if row['Low'] <= zone_upper and row['High'] >= zone_lower:
                if total_range > 0 and (candle_body / total_range) < 0.4:
                    dynamic_status = "Price Rejection Detected (Big Players Defending Zone)"
                    matched_zone = zone
                    setup_type = "Rejection"
                    break
            if abs(row['Close'] - zone) / zone <= 0.015 and candle_body < (short_term_df['Close'].pct_change().std() * row['Close']):
                dynamic_status = "Price Hold/Retest Detected (Structure Flipped & Holding)"
                matched_zone = zone
                setup_type = "Hold"
                break
                
    return dynamic_status, matched_zone, setup_type

def calculate_trade_setup(current_price, trend, zone, setup_type, zones):
    if not zone or not setup_type:
        return "ℹ️ No clear setup. Waiting for clear Price Action confirmation.", "info"
        
    upper_zones = [z for z in zones if z > current_price]
    lower_zones = [z for z in zones if z < current_price]
    
    if "Bullish" in trend or (setup_type == "Rejection" and current_price >= zone):
        entry = current_price
        stop_loss = zone * 0.985 
        target = upper_zones[0] if upper_zones else current_price * 1.05
        risk = entry - stop_loss
        reward = target - entry
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio >= 1.5:
            return f"🟢 **VALID LONG SETUP**\n\n* **Action:** BUY near {entry:.2f}\n* **Stop-Loss:** {stop_loss:.2f} (Protected by Liquidity Zone)\n* **Target:** {target:.2f}\n* **Risk-to-Reward Ratio:** 1:{rr_ratio:.2f}", "success"
        else:
            return f"⚠️ Setup found, but discarded. R:R ratio is 1:{rr_ratio:.2f} (Fails strict >= 1:1.5 rule)", "warning"
            
    elif "Bearish" in trend or (setup_type == "Rejection" and current_price < zone):
        entry = current_price
        stop_loss = zone * 1.015  
        target = lower_zones[-1] if lower_zones else current_price * 0.95
        risk = stop_loss - entry
        reward = entry - target
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio >= 1.5:
            return f"🔴 **VALID SHORT SETUP**\n\n* **Action:** SELL/SHORT near {entry:.2f}\n* **Stop-Loss:** {stop_loss:.2f} (Protected by Liquidity Zone)\n* **Target:** {target:.2f}\n* **Risk-to-Reward Ratio:** 1:{rr_ratio:.2f}", "success"
        else:
            return f"⚠️ Setup found, but discarded. R:R ratio is 1:{rr_ratio:.2f} (Fails strict >= 1:1.5 rule)", "warning"

    return "Market environment structure does not match current trade setup rules.", "info"

# --- STREAMLIT UI INPUTS ---
ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, TSLA, MSFT):", value="AAPL").upper()

if st.button("Run Analysis"):
    with st.spinner(f"Analyzing {ticker_input}..."):
        df = fetch_data(ticker_input)
        
        if df is None:
            st.error(f"Could not fetch data for ticker: {ticker_input}. Please check the symbol.")
        else:
            current_price = df['Close'].iloc[-1]
            short_term_df = df.iloc[-20:].copy()
            
            # Run calculations
            trend = analyze_market_structure(df)
            zones = find_sr_zones(df, current_price)
            dynamics, matched_zone, setup_type = check_price_dynamics(short_term_df, zones)
            trade_decision, alert_type = calculate_trade_setup(current_price, trend, matched_zone, setup_type, zones)
            
            # --- STREAMLIT OUTPUT RENDERING ---
            st.subheader(f"Results for {ticker_input}")
            
            col1, col2 = st.columns(2)
            col1.metric("Current Price", f"${current_price:.2f}")
            col2.metric("Market Trend", trend)
            
            st.markdown(f"**Active S&R Zones (Near Price):** {', '.join([f'${z:.2f}' for z in zones])}")
            st.markdown(f"**Price Action Behavior:** {dynamics}")
            if matched_zone:
                st.markdown(f"**Interacting Zone:** ${matched_zone:.2f}")
                
            st.divider()
            st.subheader("Strategy Output")
            
            # Render beautifully colored response containers based on the strategy outcome
            if alert_type == "success":
                st.success(trade_decision)
            elif alert_type == "warning":
                st.warning(trade_decision)
            else:
                st.info(trade_decision)
