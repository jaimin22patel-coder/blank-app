import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Institutional Structure Analyzer", page_icon="📈", layout="wide")

st.title("🤖 Major Structural & Institutional Zone Analyzer")
st.markdown("---")

# --- INITIALIZE WATCHLIST STORAGE & ACTIVE SELECTION ---
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["SUNPHARMA", "RELIANCE", "KOTAKBANK", "ADANIPORTS"]

if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = "SUNPHARMA"

def handle_dropdown_change():
    st.session_state["active_ticker"] = st.session_state["dropdown_selection"]
    if "manual_ticker_input" in st.session_state:
        st.session_state["manual_ticker_input"] = ""

# Sidebar Configuration
st.sidebar.header("NSE Stock Selection")

selected_from_dropdown = st.sidebar.selectbox(
    "Quick Select Stock:",
    options=st.session_state["watchlist"],
    index=st.session_state["watchlist"].index(st.session_state["active_ticker"]) if st.session_state["active_ticker"] in st.session_state["watchlist"] else 0,
    key="dropdown_selection",
    on_change=handle_dropdown_change
)

raw_ticker = st.sidebar.text_input(
    "Enter Stock Symbol Manually:", 
    value="", 
    placeholder=f"Current: {st.session_state['active_ticker']}",
    key="manual_ticker_input"
)

if raw_ticker.strip() != "":
    st.session_state["active_ticker"] = raw_ticker.upper().strip()

ticker = st.session_state["active_ticker"].replace(".NS", "")

# Add/Remove Watchlist Controls
col_add, col_rem = st.sidebar.columns(2)
if col_add.button("➕ Add", use_container_width=True):
    if ticker not in st.session_state["watchlist"] and ticker != "":
        st.session_state["watchlist"].append(ticker)
        st.session_state["active_ticker"] = ticker
        st.rerun()
if col_rem.button("❌ Remove", use_container_width=True):
    if ticker in st.session_state["watchlist"]:
        st.session_state["watchlist"].remove(ticker)
        st.session_state["active_ticker"] = st.session_state["watchlist"][0] if st.session_state["watchlist"] else ""
        st.rerun()

# --- HELPER FUNCTION: INSTITUTIONAL ZONE ENGINE ---
def extract_major_institutional_zones(df, current_cmp, zone_pct=0.015):
    """
    Identifies major structural turning points based on historical touch depth, 
    returning horizontal ranges (zones) and the absolute structural wicks for SL placement.
    """
    prices_high = df['High'].values
    prices_low = df['Low'].values
    
    swing_highs = []
    swing_high_wicks = []
    swing_lows = []
    swing_low_wicks = []
    
    # 1. Isolate structural fractal peaks and valleys
    for i in range(1, len(prices_high) - 1):
        if prices_high[i] > prices_high[i-1] and prices_high[i] > prices_high[i+1]:
            swing_highs.append(prices_high[i])
            swing_high_wicks.append(prices_high[i])
        if prices_low[i] < prices_low[i-1] and prices_low[i] < prices_low[i+1]:
            swing_lows.append(prices_low[i])
            swing_low_wicks.append(prices_low[i])
            
    # 2. Cluster pivots into dense horizontal zones
    def cluster_zones(points, original_wicks):
        clusters = {}
        for idx, p in enumerate(points):
            matched = False
            for base in clusters:
                if abs(p - base) / base <= zone_pct:
                    clusters[base]["count"] += 1
                    clusters[base]["wicks"].append(original_wicks[idx])
                    matched = True
                    break
            if not matched:
                clusters[p] = {"count": 1, "wicks": [original_wicks[idx]]}
        return clusters

    sup_clusters = cluster_zones(swing_lows, swing_low_wicks)
    res_clusters = cluster_zones(swing_highs, swing_high_wicks)
    
    # 3. Filter by touch count weight to extract the absolute MAJOR levels
    major_sups = sorted([k for k, v in sup_clusters.items() if k < current_cmp and v["count"] >= 3], reverse=True)
    major_ress = sorted([k for k, v in res_clusters.items() if k > current_cmp and v["count"] >= 3])
    
    # Default fallback boundaries if no 3-touch level exists yet
    maj_sup = major_sups[0] if len(major_sups) > 0 else current_cmp * 0.95
    maj_res = major_ress[0] if len(major_ress) > 0 else current_cmp * 1.05
    
    # 4. Extract absolute structural outer wicks for institutional protection
    sup_wicks = sup_clusters.get(maj_sup, {"wicks": [maj_sup * 0.995]})["wicks"]
    res_wicks = res_clusters.get(maj_res, {"wicks": [maj_res * 1.005]})["wicks"]
    
    absolute_lowest_wick = min(sup_wicks)
    absolute_highest_wick = max(res_wicks)
    
    return {
        "major_support_level": maj_sup,
        "major_support_zone_bottom": absolute_lowest_wick,
        "major_resistance_level": maj_res,
        "major_resistance_zone_top": absolute_highest_wick,
        "sup_touches": sup_clusters.get(maj_sup, {"count": 0})["count"],
        "res_touches": res_clusters.get(maj_res, {"count": 0})["count"]
    }

# --- ANALYTICS ENGINE ---
if ticker:
    try:
        yf_symbol = f"{ticker}.NS"
        stock = yf.Ticker(yf_symbol)
        
        df = stock.history(period="1y", interval="1d")
        df_weekly = stock.history(period="2y", interval="1wk")
        
        if not df.empty and len(df) > 50:
            latest_close = round(float(df['Close'].iloc[-1]), 2)
            prev_close = round(float(df['Close'].iloc[-2]), 2)
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"🇮🇳 Live Feed: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{latest_close:,}", delta=f"{pct_change}%")
            
            # Run Zone Extraction Engines
            daily_zones = extract_major_institutional_zones(df, latest_close)
            weekly_zones = extract_major_institutional_zones(df_weekly, latest_close, zone_pct=0.02)
            
            # --- RETAIN MATRICES FOR DISPLAY ---
            d_sup_top = round(daily_zones["major_support_level"], 2)
            d_sup_bottom = round(daily_zones["major_support_zone_bottom"], 2)
            d_res_bottom = round(daily_zones["major_resistance_level"], 2)
            d_res_top = round(daily_zones["major_resistance_zone_top"], 2)
            
            w_sup_top = round(weekly_zones["major_support_level"], 2)
            w_sup_bottom = round(weekly_zones["major_support_zone_bottom"], 2)
            w_res_bottom = round(weekly_zones["major_resistance_level"], 2)
            w_res_top = round(weekly_zones["major_resistance_zone_top"], 2)

            # --- TREND ENGINES ---
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            daily_trend = "Uptrend" if df['Close'].iloc[-1] > df['EMA_50'].iloc[-1] > df['EMA_200'].iloc[-1] else "Downtrend" if df['Close'].iloc[-1] < df['EMA_50'].iloc[-1] < df['EMA_200'].iloc[-1] else "Range-bound"

            # --- CONSERVATIVE BREAKOUT TRACKER ENGINE ---
            if latest_close > d_res_top:
                market_state = f"🚀 MAJOR DAILY BREAKOUT: Price has completely cleared the supply zone ceiling of ₹{d_res_top}."
            elif latest_close < d_sup_bottom:
                market_state = f"📉 MAJOR DAILY BREAKDOWN: Price has collapsed beneath the heavy institutional floor of ₹{d_sup_bottom}."
            else:
                market_state = f"⚖️ CONSOLIDATION: Price is safely trading between the daily major structural boundaries (₹{d_sup_top} - ₹{d_res_bottom})."

            # --- AUTOMATED ALGORITHMIC TRADE GRID SETUP ---
            trade_status = "Awaiting Valid Setup Conditions"
            setup_allowed = False
            
            # Strategy Conditions: Long Entry if price pulls down close to the major support block
            is_near_support_buy_zone = (latest_close <= d_sup_top * 1.015) and (latest_close >= d_sup_bottom)
            
            if daily_trend == "Uptrend" and is_near_support_buy_zone:
                # 1. Market Structure Stop Loss Placement (0.2% below the absolute lowest wick)
                calculated_sl = round(d_sup_bottom * 0.998, 2)
                risk_per_share = latest_close - calculated_sl
                
                if risk_per_share > 0:
                    # 2. Enforce Strict Minimum 1:1.5 Risk-to-Reward Ratio Target
                    target_1 = round(latest_close + (risk_per_share * 1.5), 2)
                    target_2 = round(latest_close + (risk_per_share * 2.5), 2)
                    
                    # 3. Overtrading Safety Filter Check
                    if target_1 <= d_res_bottom:
                        setup_allowed = True
                        trade_status = "Validated Long Setup"
                    else:
                        trade_status = "❌ Setup Blocked: Target 1 falls inside overhead resistance. Insufficient Risk-Reward Window."
            
            # --- UI RENDERING ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Trend Context Matrix")
                st.write(f"**Daily Framework Bias:** `{daily_trend}`")
                
                st.subheader("2. Key Daily Major Zones (1-Year Profile)")
                st.success(f"🟢 **Major Support Zone:** ₹{d_sup_bottom} - ₹{d_sup_top} *(Tested {daily_zones['sup_touches']} times)*")
                st.error(f"🔴 **Major Resistance Zone:** ₹{d_res_bottom} - ₹{d_res_top} *(Tested {daily_zones['res_touches']} times)*")
                
                st.subheader("3. Key Weekly Macro Zones (2-Year Profile)")
                st.markdown(f"**🔷 Weekly Heavy Floor:** ₹{w_sup_bottom} - ₹{w_sup_top} *(Tested {weekly_zones['sup_touches']} times)*")
                st.markdown(f"**🔶 Weekly Heavy Ceiling:** ₹{w_res_bottom} - ₹{w_res_top} *(Tested {weekly_zones['res_touches']} times)*")

            with col2:
                st.subheader("4. Market State Assessment")
                st.info(market_state)
                
                st.subheader("5. Algorithmic Order Block Setup")
                if not setup_allowed:
                    st.warning(f"⚠️ Status: {trade_status}")
                else:
                    st.success(f"✅ **Structure Found:** {trade_status}")
                    st.write(f"👉 **Entry Buy Zone:** Market Price (₹{latest_close})")
                    st.write(f"🛡️ **Institutional SL (Below Structure Wicks):** ₹{calculated_sl}")
                    st.write(f"🎯 **Target 1 (Strict 1:1.5 Risk RR):** ₹{target_1}")
                    st.write(f"🎯 **Target 2 (Extended 1:2.5 RR):** ₹{target_2}")
                    st.caption("Notice: This order profile is automatically blocked if target criteria cannot be mathematical achieved before hitting major resistance boundaries.")

    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
