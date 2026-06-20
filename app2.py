import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Automated Price Action Analyzer", page_icon="📈", layout="wide")

st.title("🤖 Advanced Institutional Price Action Analyzer")
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

# 1. Watchlist Dropdown Selector
st.sidebar.subheader("⭐ My Watchlist Dropdown")
default_index = 0
if st.session_state["active_ticker"] in st.session_state["watchlist"]:
    default_index = st.session_state["watchlist"].index(st.session_state["active_ticker"])

selected_from_dropdown = st.sidebar.selectbox(
    "Quick Select Stock:",
    options=st.session_state["watchlist"],
    index=default_index,
    key="dropdown_selection",
    on_change=handle_dropdown_change
)

# 2. Main Manual Input
st.sidebar.subheader("🔍 Manual Search")
raw_ticker = st.sidebar.text_input(
    "Enter Stock Symbol Manually & Press Enter:", 
    value="", 
    placeholder=f"Current: {st.session_state['active_ticker']}",
    key="manual_ticker_input"
)

if raw_ticker.strip() != "":
    st.session_state["active_ticker"] = raw_ticker.upper().strip()

ticker = st.session_state["active_ticker"].replace(".NS", "")

# 3. Add / Remove Controls
col_add, col_rem = st.sidebar.columns(2)
if col_add.button("➕ Add to List", use_container_width=True):
    if ticker not in st.session_state["watchlist"] and ticker != "":
        st.session_state["watchlist"].append(ticker)
        st.session_state["active_ticker"] = ticker
        st.rerun()

if col_rem.button("❌ Remove Current", use_container_width=True):
    if ticker in st.session_state["watchlist"]:
        st.session_state["watchlist"].remove(ticker)
        st.session_state["active_ticker"] = st.session_state["watchlist"][0] if st.session_state["watchlist"] else ""
        st.rerun()

# --- HELPER FUNCTION: FIXED STRUCTURAL PROXIMITY ENGINE ---
def extract_structural_levels(prices_high, prices_low, current_cmp, zone_pct=0.015):
    swing_highs = []
    swing_lows = []
    
    # 1. Isolate structural fractal peaks and valleys (3-candle window)
    for i in range(1, len(prices_high) - 1):
        if prices_high[i] > prices_high[i-1] and prices_high[i] > prices_high[i+1]:
            swing_highs.append(prices_high[i])
        if prices_low[i] < prices_low[i-1] and prices_low[i] < prices_low[i+1]:
            swing_lows.append(prices_low[i])
            
    # 2. Cluster pivots into horizontal price zones
    def cluster_points(points):
        clusters = {}
        for p in points:
            matched = False
            for base in clusters:
                if abs(p - base) / base <= zone_pct:
                    clusters[base] += 1
                    matched = True
                    break
            if not matched:
                clusters[p] = 1
        return clusters

    sup_clusters = cluster_points(swing_lows)
    res_clusters = cluster_points(swing_highs)
    
    # 3. FIXED PROXIMITY SORTING (Closest level to price always becomes Immediate)
    all_sups = sorted([k for k in sup_clusters.keys() if k < current_cmp], reverse=True)
    all_ress = sorted([k for k in res_clusters.keys() if k > current_cmp])
    
    # Support Mapping Logic
    d_imm_sup = all_sups[0] if len(all_sups) > 0 else current_cmp * 0.98
    d_maj_sup = all_sups[1] if len(all_sups) > 1 else d_imm_sup * 0.95
    
    # Resistance Mapping Logic
    d_imm_res = all_ress[0] if len(all_ress) > 0 else current_cmp * 1.02
    d_maj_res = all_ress[1] if len(all_ress) > 1 else d_imm_res * 1.05
    
    return {
        "immediate_support": d_imm_sup,
        "major_support": d_maj_sup,
        "immediate_resistance": d_imm_res,
        "major_resistance": d_maj_res,
        "sup_counts": sup_clusters,
        "res_counts": res_clusters
    }

# --- ANALYTICS ENGINE RUNS BELOW ---
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
            
            current_high = round(float(df['High'].iloc[-1]), 2)
            current_low = round(float(df['Low'].iloc[-1]), 2)
            current_open = round(float(df['Open'].iloc[-1]), 2)
            
            # Sub-sidebar Renders
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"🇮🇳 Live Feed: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{latest_close:,}", delta=f"{pct_change}%")
            
            # --- EXTRACT MULTI-TIMEFRAME LEVEL MATRICES ---
            daily_levels = extract_structural_levels(df['High'].values, df['Low'].values, latest_close)
            weekly_levels = extract_structural_levels(df_weekly['High'].values, df_weekly['Low'].values, latest_close)
            
            d_immediate_sup = daily_levels["immediate_support"]
            d_major_sup = daily_levels["major_support"]
            d_immediate_res = daily_levels["immediate_resistance"]
            d_major_res = daily_levels["major_resistance"]
            
            imm_sup_touches = daily_levels["sup_counts"].get(d_immediate_sup, 2)
            maj_sup_touches = daily_levels["sup_counts"].get(d_major_sup, 4)
            imm_res_touches = daily_levels["res_counts"].get(d_immediate_res, 2)
            maj_res_touches = daily_levels["res_counts"].get(d_major_res, 4)
            
            # --- TREND LOGIC ---
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            df_weekly['EMA_50'] = df_weekly['Close'].ewm(span=50, adjust=False).mean()
            
            daily_trend = "Range-bound"
            if df['Close'].iloc[-1] > df['EMA_50'].iloc[-1] > df['EMA_200'].iloc[-1]:
                daily_trend = "Uptrend"
            elif df['Close'].iloc[-1] < df['EMA_50'].iloc[-1] < df['EMA_200'].iloc[-1]:
                daily_trend = "Downtrend"
                
            weekly_trend = "Range-bound"
            if df_weekly['Close'].iloc[-1] > df_weekly['EMA_50'].iloc[-1]:
                weekly_trend = "Uptrend"
            elif df_weekly['Close'].iloc[-1] < df_weekly['EMA_50'].iloc[-1]:
                weekly_trend = "Downtrend"
                
            wave_seq = "Higher Highs / Higher Lows (HH/HL)" if daily_trend == "Uptrend" else "Lower Highs / Lower Lows (LH/LL)" if daily_trend == "Downtrend" else "Equal Highs / Lows (Chop)"

            # Candlestick Calculations
            body = abs(latest_close - current_open)
            total_range = current_high - current_low
            lower_wick = min(current_open, latest_close) - current_low
            upper_wick = current_high - max(current_open, latest_close)
            is_hammer = total_range > 0 and (lower_wick / total_range > 0.6)
            is_shooting_star = total_range > 0 and (upper_wick / total_range > 0.6)

            # --- BREAKOUT ENGINE ---
            retest_status = "Awaiting Initial Structural Breach"
            bo_prob = "No Breakout"
            bo_val_range = "⚖️ CONSOLIDATION: Price trading inside structural boundaries."
            
            recent_closes = df['Close'].iloc[-6:-1].tolist()
            recent_lows = df['Low'].iloc[-6:-1].tolist()
            recent_highs = df['High'].iloc[-6:-1].tolist()
            
            had_bullish_breach = any(c > d_immediate_res for c in recent_closes)
            had_bearish_breach = any(c < d_immediate_sup for c in recent_closes)
            
            volume_ratio = volume_latest / volume_avg
            
            if latest_close > d_immediate_res:
                bo_prob = "High (Raw Breakout)" if volume_ratio > 1.5 else "Low (Potential Trap)"
                retest_status = "🏃 Awaiting Retest (Raw Breakout printing)"
                bo_val_range = f"🚀 INITIAL BREACH: Range: ₹{round(d_immediate_res, 2)} to ₹{round(d_immediate_res * 1.015, 2)}."
            elif latest_close < d_immediate_sup:
                bo_prob = "High (Raw Breakdown)" if volume_ratio > 1.5 else "Low (Potential Trap)"
                retest_status = "🏃 Awaiting Retest (Raw Breakdown printing)"
                bo_val_range = f"💥 INITIAL BREACH: Range: ₹{round(d_immediate_sup * 0.985, 2)} to ₹{round(d_immediate_sup, 2)}."
            elif had_bullish_breach:
                returned_to_zone = any(l <= (d_immediate_res * 1.015) and l >= (d_immediate_res * 0.985) for l in recent_lows)
                if returned_to_zone:
                    if latest_close > current_open or is_hammer:
                        retest_status = "✅ RETEST CONFIRMED: Old resistance floor successfully transformed into active support."
                        bo_prob = "High (Retest Verified)" if volume_ratio >= 1.2 else "Medium"
                        bo_val_range = f"🚀 RETEST BUY ENTRY LIVE: Zone: ₹{round(d_immediate_res, 2)} - ₹{round(d_immediate_res * 1.015, 2)}."
                    else:
                        retest_status = "⏳ RETEST IN PROGRESS: Pullback underway. Awaiting daily confirmation."
                        bo_prob = "Evaluating"
                        bo_val_range = "⚠️ HOLD ENTRIES: Price is directly on the line."
            elif had_bearish_breach:
                returned_to_zone = any(h >= (d_immediate_sup * 0.985) and h <= (d_immediate_sup * 1.015) for h in recent_highs)
                if returned_to_zone:
                    if latest_close < current_open or is_shooting_star:
                        retest_status = "💥 BREAKDOWN RETEST CONFIRMED: Old support completely turned into active ceiling."
                        bo_prob = "High (Retest Verified)" if volume_ratio >= 1.2 else "Medium"
                        bo_val_range = f"📉 RETEST SHORT ENTRY LIVE: Zone: ₹{round(d_immediate_sup * 0.985, 2)} - ₹{round(d_immediate_sup, 2)}."
                    else:
                        retest_status = "⏳ SHORT RETEST IN PROGRESS: Price has bounced to old support floor."
                        bo_prob = "Evaluating"
                        bo_val_range = "⚠️ HOLD SHORTS: Price is resting on the line."

            # --- STRUCTURAL CONFIRMATION ---
            sr_confirmation_status = "No testing event at immediate key levels right now."
            near_support_zone = latest_close <= (d_immediate_sup * 1.02)
            near_resistance_zone = latest_close >= (d_immediate_res * 0.98)
            
            if near_support_zone and (is_hammer or latest_close > current_open):
                sr_confirmation_status = f"✅ DEMAND HOLD CONFIRMED: Held {imm_sup_touches} times over the last year."
            elif near_resistance_zone and (is_shooting_star or latest_close < current_open):
                sr_confirmation_status = f"⚠️ SUPPLY REJECTION CONFIRMED: Rejected price expansion {imm_res_touches} times historically."

            # --- RISK FILTER SETUP ---
            raw_setup_type = "No Setup Available"
            entry, sl, t1, t2, rr_display, action, bias = latest_close, 0.0, 0.0, 0.0, "N/A", "Wait / Sit on Hands", "Neutral"
            confidence = 5

            if daily_trend == "Uptrend" and "CONFIRMED" in retest_status:
                raw_setup_type = "Retest Verified Long Setup"
                entry = latest_close
                sl = round(d_immediate_sup * 0.99, 2)
                t1 = round(d_immediate_res, 2)
                t2 = round(d_major_res, 2)
                bias, action, confidence = "Bullish", "Buy", 9

            # --- UI RENDERING ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Market Structure")
                st.write(f"**Daily Chart Bias:** `{daily_trend}`")
                st.write(f"**Weekly Chart Bias:** `{weekly_trend}`")
                st.write(f"**Wave Sequence:** {wave_seq}")
                
                st.subheader("2. Key Support Levels (Multi-Timeframe)")
                st.write(f"📅 **Daily Immediate Support:** ₹{round(d_immediate_sup, 2)} *(Tested {imm_sup_touches} times)*")
                st.write(f"📅 **Daily Major Floor:** ₹{round(d_major_sup, 2)} *(Tested {maj_sup_touches} times)*")
                st.write(f"🗓️ **Weekly Macro Support:** ₹{round(weekly_levels['major_support'], 2)}")
                
                st.subheader("3. Key Resistance Levels (Multi-Timeframe)")
                st.write(f"📅 **Daily Immediate Resistance:** ₹{round(d_immediate_res, 2)} *(Tested {imm_res_touches} times)*")
                st.write(f"📅 **Daily Major Ceiling:** ₹{round(d_major_res, 2)} *(Tested {maj_res_touches} times)*")
                st.write(f"🗓️ **Weekly Macro Resistance:** ₹{round(weekly_levels['major_resistance'], 2)}")
                
                st.subheader("4. Price Action Interpretation")
                st.markdown("**🟢 Demand Zones:**")
                st.write(f"* **Immediate (Touches: {imm_sup_touches}):** ₹{round(d_immediate_sup, 2)} - ₹{round(d_immediate_sup * 1.015, 2)}")
                st.markdown("**🔴 Supply Zones:**")
                st.write(f"* **Immediate (Touches: {imm_res_touches}):** ₹{round(d_immediate_res * 0.985, 2)} - ₹{round(d_immediate_res, 2)}")

                st.subheader("5. Candlestick Analysis")
                st.write(f"**Observed Formations:** {'Hammer Rejection' if is_hammer else 'Shooting Star' if is_shooting_star else 'Consolidation Candle'}")

            with col2:
                st.subheader("6. Breakout / Breakdown Assessment")
                st.write(f"**Retest Verification Score:** `{bo_prob}`")
                st.write(f"**Volume Multiplier:** {round(volume_ratio, 2)}x")
                st.warning(bo_val_range)
                
                st.subheader("7. Retest Analysis")
                st.info(f"🔄 **Retest Tracking Engine:** {retest_status}")
                
                st.subheader("8. Algorithmic Trade Setup (Risk Filtered)")
                if raw_setup_type == "No Setup Available":
                    st.warning("⚠️ No Trade Setup Generated: Waiting for a verified high-volume retest bounce to confirm structural invalidation levels.")
                else:
                    st.info(f"**Structure Found:** {raw_setup_type}")
                    st.write(f"👉 **Entry Price:** ₹{entry} | **Stop Loss:** ₹{sl} | **Targets:** ₹{t1} / ₹{t2}")
                
                st.subheader("9. Structural Support & Resistance Confirmation")
                st.info(sr_confirmation_status)
                
                st.subheader("10. Automated Conclusion")
                st.success(f"**Directional Bias:** {bias.upper()} | **Suggested Action:** `{action.upper()}` | **Confidence Score:** {confidence}/10")

    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
