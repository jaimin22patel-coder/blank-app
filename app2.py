import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Institutional Structure Analyzer", page_icon="📈", layout="wide")

st.title("🤖 Advanced Price Action & Market Structure Engine")
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

# --- HELPER FUNCTION: CORE STRUCTURAL ZONE ENGINE ---
def extract_major_institutional_zones(df, current_cmp, zone_pct=0.015):
    prices_high = df['High'].values
    prices_low = df['Low'].values
    
    swing_highs = []
    swing_high_wicks = []
    swing_lows = []
    swing_low_wicks = []
    
    # Isolate structural fractal peaks and valleys
    for i in range(1, len(prices_high) - 1):
        if prices_high[i] > prices_high[i-1] and prices_high[i] > prices_high[i+1]:
            swing_highs.append(prices_high[i])
            swing_high_wicks.append(prices_high[i])
        if prices_low[i] < prices_low[i-1] and prices_low[i] < prices_low[i+1]:
            swing_lows.append(prices_low[i])
            swing_low_wicks.append(prices_low[i])
            
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
    
    major_sups = sorted([k for k, v in sup_clusters.items() if k < current_cmp and v["count"] >= 3], reverse=True)
    major_ress = sorted([k for k, v in res_clusters.items() if k > current_cmp and v["count"] >= 3])
    
    maj_sup = major_sups[0] if len(major_sups) > 0 else current_cmp * 0.95
    maj_res = major_ress[0] if len(major_ress) > 0 else current_cmp * 1.05
    
    sup_wicks = sup_clusters.get(maj_sup, {"wicks": [maj_sup * 0.995]})["wicks"]
    res_wicks = res_clusters.get(maj_res, {"wicks": [maj_res * 1.005]})["wicks"]
    
    return {
        "major_support_level": maj_sup,
        "major_support_zone_bottom": min(sup_wicks),
        "major_resistance_level": maj_res,
        "major_resistance_zone_top": max(res_wicks),
        "sup_touches": sup_clusters.get(maj_sup, {"count": 0})["count"],
        "res_touches": res_clusters.get(maj_res, {"count": 0})["count"]
    }

# --- HELPER FUNCTION: MARKET STRUCTURE SHIFT (MSS) DETECTOR ---
def detect_market_structure_shift(df):
    """
    Tracks sequential pivot points over a 20-day trailing sequence 
    to classify structural trend shifts (HH/HL vs LH/LL).
    """
    highs = df['High'].rolling(window=5, center=True).max().dropna().tolist()[-5:]
    lows = df['Low'].rolling(window=5, center=True).min().dropna().tolist()[-5:]
    
    if len(highs) >= 4 and len(lows) >= 4:
        # Check for structural changes
        is_hh = highs[-1] > highs[-2] and highs[-2] > highs[-3]
        is_hl = lows[-1] > lows[-2] and lows[-2] > lows[-3]
        is_lh = highs[-1] < highs[-2] and highs[-2] < highs[-3]
        is_ll = lows[-1] < lows[-2] and lows[-2] < lows[-3]
        
        if is_hh and is_hl:
            return "📈 Bullish Structure (Higher Highs / Higher Lows)", "Bullish"
        elif is_lh and is_ll:
            return "📉 Bearish Structure (Lower Highs / Lower Lows)", "Bearish"
        elif highs[-1] > highs[-2] and lows[-1] < lows[-2]:
            return "🔄 Structural Shift Detected: High Volatility Expansion", "Neutral"
        elif highs[-1] < highs[-2] and lows[-1] > lows[-2]:
            return "⚖️ Structural Shift Detected: Range Compression / Consolidation", "Neutral"
            
    return "⚖️ Balanced Structural Consolidation", "Neutral"

# --- ANALYTICS RUN ---
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
            
            volume_latest = int(df['Volume'].iloc[-1])
            volume_avg = int(df['Volume'].rolling(window=20).mean().iloc[-1])
            volume_ratio = volume_latest / volume_avg
            
            current_high = round(float(df['High'].iloc[-1]), 2)
            current_low = round(float(df['Low'].iloc[-1]), 2)
            current_open = round(float(df['Open'].iloc[-1]), 2)
            
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"🇮🇳 Live Feed: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{latest_close:,}", delta=f"{pct_change}%")
            
            # 1. PROCESS MARKET STRUCTURE SHIFTS (MSS)
            structure_desc, trend_bias = detect_market_structure_shift(df)
            
            # Extract Institutional Zone Boundaries
            daily_zones = extract_major_institutional_zones(df, latest_close)
            weekly_zones = extract_major_institutional_zones(df_weekly, latest_close, zone_pct=0.02)
            
            d_sup_top = round(daily_zones["major_support_level"], 2)
            d_sup_bottom = round(daily_zones["major_support_zone_bottom"], 2)
            d_res_bottom = round(daily_zones["major_resistance_level"], 2)
            d_res_top = round(daily_zones["major_resistance_zone_top"], 2)

            # Candlestick Anatomy
            total_range = current_high - current_low
            lower_wick = min(current_open, latest_close) - current_low
            upper_wick = current_high - max(current_open, latest_close)
            is_hammer = total_range > 0 and (lower_wick / total_range > 0.55)
            is_shooting_star = total_range > 0 and (upper_wick / total_range > 0.55)

            # 2. PROCESS BREAKOUTS & BREAKDOWNS (With Volume Filters)
            # 3. PROCESS RETESTS (Look back across trailing 5 sessions)
            breakout_status = "⚖️ Neutral: Consolidating cleanly within major structural zones."
            retest_status = "⏳ No active retest pattern flagged."
            setup_allowed = False
            trade_status = "Scanning structural boundaries..."
            
            recent_closes = df['Close'].iloc[-6:-1].tolist()
            recent_lows = df['Low'].iloc[-6:-1].tolist()
            recent_highs = df['High'].iloc[-6:-1].tolist()
            
            had_bullish_breakout = any(c > d_res_top for c in recent_closes)
            had_bearish_breakdown = any(c < d_sup_bottom for c in recent_closes)
            
            if latest_close > d_res_top:
                if volume_ratio > 1.4:
                    breakout_status = f"🚀 VERIFIED INSTITUTIONAL BREAKOUT: Price has convincingly breached the major ceiling of ₹{d_res_top} on high volume ({round(volume_ratio,2)}x)."
                else:
                    breakout_status = f"⚠️ LIQUIDITY TRAP WARNING: Price closed above ₹{d_res_top} but lacks institutional volume backing ({round(volume_ratio,2)}x)."
            elif latest_close < d_sup_bottom:
                if volume_ratio > 1.4:
                    breakout_status = f"💥 VERIFIED INSTITUTIONAL BREAKDOWN: Heavy selling pressure has blown past the major floor of ₹{d_sup_bottom}."
                else:
                    breakout_status = f"⚠️ BEAR TRAP WARNING: Price slipped below ₹{d_sup_bottom} on anemic volume."
            
            # Process Retests and Confirmed Structural Shifts
            if had_bullish_breakout and (current_low <= d_res_top * 1.01) and (latest_close >= d_res_bottom):
                if latest_close > current_open or is_hammer:
                    retest_status = f"✅ RETEST CONFIRMED: Previous Major Resistance (₹{d_res_bottom}) was tested and successfully held as an active support block."
                    if trend_bias == "Bullish":
                        setup_allowed = True
                        trade_status = "Institutional Breakout-Retest Long Verified"
            elif had_bearish_breakdown and (current_high >= d_sup_bottom * 0.99) and (latest_close <= d_sup_top):
                if latest_close < current_open or is_shooting_star:
                    retest_status = f"💥 BREAKDOWN RETEST CONFIRMED: Previous Major Support floor has flipped into a firm supply ceiling."

            # 4. PROCESS REAL-TIME PRICE HOLDS & REJECTIONS
            rejection_status = "No active testing events printing at critical boundaries right now."
            is_testing_support_zone = (latest_close <= d_sup_top * 1.015) and (latest_close >= d_sup_bottom * 0.995)
            is_testing_resistance_zone = (latest_close >= d_res_bottom * 0.985) and (latest_close <= d_res_top * 1.005)
            
            if is_testing_support_zone:
                if is_hammer or latest_close > current_open:
                    rejection_status = f"🟢 PRICE HOLD CONFIRMED: Heavy buying interest active inside the institutional support block (₹{d_sup_bottom} - ₹{d_sup_top}). Wicks show order absorption."
                    if trend_bias == "Bullish" and not setup_allowed:
                        setup_allowed = True
                        trade_status = "Major Structural Demand Floor Bounce"
                else:
                    rejection_status = "⏳ Price entering institutional demand zone. Monitoring the daily candle print for a structural hold."
            elif is_testing_resistance_zone:
                if is_shooting_star or latest_close < current_open:
                    rejection_status = f"🔴 SUPPLY REJECTION CONFIRMED: Institutions are actively defending the major ceiling zone (₹{d_res_bottom} - ₹{d_res_top}). Upper shadows confirm distribution."

            # --- PROCESS RISK EXECUTION GRID (STRICT > 1:1.5 RR & PROTECTION SL) ---
            calculated_sl, target_1, target_2 = 0.0, 0.0, 0.0
            if setup_allowed:
                # Set Stop Loss 0.2% below the absolute lowest structural wick
                calculated_sl = round(d_sup_bottom * 0.998, 2)
                risk_per_share = latest_close - calculated_sl
                
                if risk_per_share > 0:
                    target_1 = round(latest_close + (risk_per_share * 1.5), 2)
                    target_2 = round(latest_close + (risk_per_share * 2.5), 2)
                    
                    # Overtrading Risk Filter Guardrail
                    if target_1 > d_res_bottom:
                        setup_allowed = False
                        trade_status = f"❌ Trade Setup Aborted: Target 1 (₹{target_1}) requires breaking the major overhead ceiling (₹{d_res_bottom}) beforehand. Poor risk-reward execution space."

            # --- UI RENDERING ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Sequential Market Structure Shifts (MSS)")
                st.info(structure_desc)
                
                st.subheader("2. Key Daily Major Structural Zones (1-Year Profile)")
                st.success(f"🟢 **Institutional Support Block:** ₹{d_sup_bottom} - ₹{d_sup_top} *(Tested {daily_zones['sup_touches']} times)*")
                st.error(f"🔴 **Institutional Resistance Block:** ₹{d_res_bottom} - ₹{d_res_top} *(Tested {daily_zones['res_touches']} times)*")
                
                st.subheader("3. Key Weekly Macro Zones (2-Year Profile)")
                st.markdown(f"**🔷 Weekly Heavy Floor:** ₹{round(weekly_zones['major_support_zone_bottom'], 2)} - ₹{round(weekly_zones['major_support_level'], 2)}")
                st.markdown(f"**🔶 Weekly Heavy Ceiling:** ₹{round(weekly_zones['major_resistance_level'], 2)} - ₹{round(weekly_zones['major_resistance_zone_top'], 2)}")

            with col2:
                st.subheader("4. Breakout & Breakdown Assessment")
                st.write(breakout_status)
                st.caption(f"Current Volume Activity: {round(volume_ratio, 2)}x of the baseline 20-day average.")
                
                st.subheader("5. Retest Tracker & Structural Rejections")
                st.warning(f"🔄 **Retest Analysis:** {retest_status}")
                st.info(f"⚡ **Zone Price Action:** {rejection_status}")
                
                st.subheader("6. Algorithmic Risk Execution Setup")
                if not setup_allowed:
                    st.warning(f"⚠️ **Order Desk Status:** {trade_status}")
                else:
                    st.success(f"✅ **Execution Order Validated:** {trade_status}")
                    st.write(f"👉 **Entry Buy Price (Deep Zone Fill):** ₹{latest_close}")
                    st.write(f"🛡️ **Institutional Protection SL:** ₹{calculated_sl}")
                    st.write(f"🎯 **Target 1 (Strict 1:1.5 RR Minimum):** ₹{target_1}")
                    st.write(f"🎯 **Target 2 (Extended 1:2.5 RR Target):** ₹{target_2}")

    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
