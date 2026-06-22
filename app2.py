import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import os

# Page Configuration
st.set_page_config(page_title="Price Action Strategy Desk", page_icon="📈", layout="wide")

st.title("🤖 Pure Price Action & Institutional Structure Desk")
st.markdown("---")

# --- PERMANENT STORAGE ENGINE ---
WATCHLIST_FILE = "watchlist.txt"
DEFAULT_WATCHLIST = ["SUNPHARMA", "RELIANCE", "KOTAKBANK", "ADANIPORTS"]

def load_saved_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            stocks = [line.strip().upper() for line in f.readlines() if line.strip()]
            if stocks:
                return stocks
    return DEFAULT_WATCHLIST.copy()

def save_watchlist_to_disk(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        for stock in watchlist:
            f.write(f"{stock}\n")

# --- INITIALIZE WATCHLIST STORAGE & ACTIVE SELECTION ---
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_saved_watchlist()

if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = st.session_state["watchlist"][0]

def handle_dropdown_change():
    st.session_state["active_ticker"] = st.session_state["dropdown_selection"]
    if "manual_ticker_input" in st.session_state:
        st.session_state["manual_ticker_input"] = ""

# Sidebar Controls
st.sidebar.header("NSE Asset Controller")

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

# Add/Remove Buttons
col_add, col_rem = st.sidebar.columns(2)
if col_add.button("➕ Add", use_container_width=True):
    if ticker not in st.session_state["watchlist"] and ticker != "":
        st.session_state["watchlist"].append(ticker)
        st.session_state["active_ticker"] = ticker
        save_watchlist_to_disk(st.session_state["watchlist"])
        st.rerun()
if col_rem.button("❌ Remove", use_container_width=True):
    if ticker in st.session_state["watchlist"]:
        st.session_state["watchlist"].remove(ticker)
        st.session_state["active_ticker"] = st.session_state["watchlist"][0] if st.session_state["watchlist"] else ""
        save_watchlist_to_disk(st.session_state["watchlist"])
        st.rerun()

# --- OPTION 3 MULTI-LAYER STRUCTURE DETECTOR ENGINE ---
def calculate_dual_layer_mss(df_full):
    highs = df_full['High'].tolist()
    lows = df_full['Low'].tolist()
    
    internal_highs = highs[-84:]
    internal_lows = lows[-84:]
    
    def extract_pivots(h_arr, l_arr, left_right_strength=3):
        p_highs, p_lows = [], []
        for i in range(left_right_strength, len(h_arr) - left_right_strength):
            if h_arr[i] == max(h_arr[i - left_right_strength : i + left_right_strength + 1]):
                p_highs.append(h_arr[i])
            if l_arr[i] == min(l_arr[i - left_right_strength : i + left_right_strength + 1]):
                p_lows.append(l_arr[i])
        return p_highs, p_lows

    ext_highs, ext_lows = extract_pivots(highs, lows, left_right_strength=10)
    int_highs, int_lows = extract_pivots(internal_highs, internal_lows, left_right_strength=3)
    
    ext_bias = "Neutral / Consolidation"
    if len(ext_highs) >= 2 and len(ext_lows) >= 2:
        if ext_highs[-1] > ext_highs[-2] and ext_lows[-1] > ext_lows[-2]:
            ext_bias = "📈 Bullish Macro Trend"
        elif ext_highs[-1] < ext_highs[-2] and ext_lows[-1] < ext_lows[-2]:
            ext_bias = "📉 Bearish Macro Trend"
            
    int_bias = "Neutral"
    if len(int_highs) >= 2 and len(int_lows) >= 2:
        if int_highs[-1] > int_highs[-2] and int_lows[-1] > int_lows[-2]:
            int_bias = "Bullish"
        elif int_highs[-1] < int_highs[-2] and int_lows[-1] < int_lows[-2]:
            int_bias = "Bearish"

    if "Bullish" in ext_bias and int_bias == "Bullish":
        summary = "✅ MACRO & LOCAL ALIGNED BULLISH: Strong macro uptrend with confirmed local momentum."
        verdict = "Bullish"
    elif "Bullish" in ext_bias and int_bias == "Bearish":
        summary = "🔄 BULLISH RETRACEMENT: Major long-term uptrend experiencing a local pullback into discount values."
        verdict = "Retracement"
    elif "Bearish" in ext_bias and int_bias == "Bearish":
        summary = "❌ FULL BEARISH DISTRIBUTION: Macro and local trends are printing synchronous lower structures."
        verdict = "Bearish"
    else:
        summary = f"⚖️ MIXED STRUCTURE MATRIX: External: {ext_bias} | Internal: {int_bias} local."
        verdict = "Neutral"
        
    return summary, verdict, ext_bias, int_bias

# --- UNIFIED DUAL-LAYER STRUCTURAL ZONE CALCULATOR ---
def extract_pure_order_blocks(df, current_cmp, lookback_bars, strength, zone_pct):
    """
    Unified extraction tool to pull structural blocks using precise 
    bar constraints and pivot configurations on daily charts.
    """
    df_sliced = df.iloc[-lookback_bars:]
    highs = df_sliced['High'].values
    lows = df_sliced['Low'].values
    closes = df_sliced['Close'].values
    opens = df_sliced['Open'].values
    
    swing_highs, swing_high_tops = [], []
    swing_lows, swing_low_bottoms = [], []
    
    for i in range(strength, len(df_sliced) - strength):
        if highs[i] == max(highs[i - strength : i + strength + 1]):
            swing_highs.append(min(opens[i], closes[i])) 
            swing_high_tops.append(highs[i])             
        if lows[i] == min(lows[i - strength : i + strength + 1]):
            swing_lows.append(max(opens[i], closes[i]))  
            swing_low_bottoms.append(lows[i])            
            
    def build_clusters(bases, extremities, find_above):
        clusters = {}
        for idx, base in enumerate(bases):
            matched = False
            for key in clusters:
                if abs(base - key) / key <= zone_pct:
                    clusters[key]["count"] += 1
                    clusters[key]["extremes"].append(extremities[idx])
                    matched = True
                    break
            if not matched:
                clusters[base] = {"count": 1, "extremes": [extremities[idx]]}
                
        sorted_clusters = sorted(clusters.items(), key=lambda x: x[1]["count"], reverse=True)
        
        if find_above:
            filtered = [c for c in sorted_clusters if c[0] > current_cmp]
        else:
            filtered = [c for c in sorted_clusters if c[0] < current_cmp]
            
        return filtered[0] if len(filtered) > 0 else (None, {"count": 1, "extremes": [current_cmp * (1.05 if find_above else 0.95)]})

    sup_key, sup_data = build_clusters(swing_lows, swing_low_bottoms, find_above=False)
    res_key, res_data = build_clusters(swing_highs, swing_high_tops, find_above=True)
    
    s_top = sup_key if sup_key else current_cmp * 0.96
    s_bottom = min(sup_data["extremes"])
    
    r_bottom = res_key if res_key else current_cmp * 1.04
    r_top = max(res_data["extremes"])
    
    return s_top, s_bottom, r_bottom, r_top, sup_data["count"], res_data["count"]

# --- MAIN EXECUTION FRAMEWORK ---
if ticker:
    try:
        yf_symbol = f"{ticker}.NS"
        stock = yf.Ticker(yf_symbol)
        
        # Single Source of Truth Data Silo: 14 Months of Daily Data
        df_daily_full = stock.history(period="14mo", interval="1d")    
        
        if not df_daily_full.empty and len(df_daily_full) > 100:
            cmp = round(float(df_daily_full['Close'].iloc[-1]), 2)
            p_close = round(float(df_daily_full['Close'].iloc[-2]), 2)
            change = round(((cmp - p_close) / p_close) * 100, 2)
            
            v_latest = int(df_daily_full['Volume'].iloc[-1])
            v_avg = int(df_daily_full['Volume'].rolling(window=20).mean().iloc[-1])
            v_mult = v_latest / v_avg if v_avg > 0 else 1.0
            
            c_open = round(float(df_daily_full['Open'].iloc[-1]), 2)
            c_high = round(float(df_daily_full['High'].iloc[-1]), 2)
            c_low = round(float(df_daily_full['Low'].iloc[-1]), 2)
            
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"🇮🇳 Asset Vector: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{cmp:,}", delta=f"{change}%")
            
            # 1. Execute Option 3 Market Structure Shifts
            mss_msg, trend_bias, ext_bias, int_bias = calculate_dual_layer_mss(df_daily_full)
            
            # 2. Execute Unified Internal vs. External Structural Zones Mapping
            # Internal (Section 2 Equivalent): Lookback 4 Months (84 bars), Pivot Strength 3, Range Window 1.2%
            int_s_top, int_s_bottom, int_r_bottom, int_r_top, int_s_hits, int_r_hits = extract_pure_order_blocks(
                df_daily_full, cmp, lookback_bars=84, strength=3, zone_pct=0.012
            )
            # External (Section 3 Equivalent): Lookback 14 Months (294 bars), Pivot Strength 10, Range Window 2.0%
            ext_s_top, ext_s_bottom, ext_r_bottom, ext_r_top, ext_s_hits, ext_r_hits = extract_pure_order_blocks(
                df_daily_full, cmp, lookback_bars=len(df_daily_full), strength=10, zone_pct=0.020
            )
            
            # Candlestick Signature Parsing
            c_range = c_high - c_low
            l_wick = min(c_open, cmp) - c_low
            u_wick = c_high - max(c_open, cmp)
            
            is_hammer = c_range > 0 and (l_wick / c_range >= 0.55)
            is_shooting_star = c_range > 0 and (u_wick / c_range >= 0.55)
            
            prev_open = float(df_daily_full['Open'].iloc[-2])
            prev_close_val = float(df_daily_full['Close'].iloc[-2])
            is_bullish_engulfing = cmp > c_open and prev_close_val < prev_open and cmp > prev_open and c_open < prev_close_val
            
            candle_pattern = "Standard Candle"
            if is_hammer: candle_pattern = "💎 Institutional Hammer (Liquidity Grab)"
            elif is_shooting_star: candle_pattern = "🛸 Shooting Star (Supply Rejection)"
            elif is_bullish_engulfing: candle_pattern = "🔥 Bullish Engulfing (Institutional Displacement)"

            # Breakout and Strike Counters tied to the Internal Execution Zone
            breakout_status = "⚖️ Rangebound: Price is trading inside local structural boundaries."
            retest_status = "⏳ No active breakout retest flagged."
            setup_ready = False
            desk_msg = "Awaiting institutional setup conditions..."
            
            recent_highs_list = df_daily_full['High'].iloc[-20:].tolist()
            recent_lows_list = df_daily_full['Low'].iloc[-20:].tolist()
            recent_closes_list = df_daily_full['Close'].iloc[-20:].tolist()
            
            ceiling_strikes = sum(1 for h, c in zip(recent_highs_list, recent_closes_list) if h >= int_r_bottom and c <= int_r_top)
            floor_strikes = sum(1 for l, c in zip(recent_lows_list, recent_closes_list) if l <= int_s_top and c >= int_s_bottom)
            
            historic_closes = df_daily_full['Close'].iloc[-7:-1].tolist()
            had_local_breakout = any(hc > int_r_top for hc in historic_closes)
            
            # Modified Breakout Logic evaluating Internal Limits
            if cmp > int_r_top:
                if v_mult >= 1.4:
                    breakout_status = f"🚀 VERIFIED LOCAL BREAKOUT: Confirmed body close above internal ceiling ₹{round(int_r_top, 2)} on heavy volume ({round(v_mult,2)}x)."
                else:
                    breakout_status = f"⚠️ LIQUIDITY TRAP WARNING: Outside close printed at ₹{cmp}, but volume fails institutional threshold ({round(v_mult,2)}x)."
            elif cmp < int_s_bottom:
                if v_mult >= 1.4:
                    breakout_status = f"💥 VERIFIED LOCAL BREAKDOWN: Strong structural close below the local floor of ₹{round(int_s_bottom, 2)}."
            
            if had_local_breakout and (c_low <= int_r_top * 1.01) and (cmp >= int_r_bottom):
                if cmp > c_open or is_hammer:
                    retest_status = f"✅ LOCAL RETEST CONFIRMED: Previous Local Ceiling (₹{round(int_r_bottom, 2)}) successfully flipped and defended as support."
                    if trend_bias in ["Bullish", "Retracement"]:
                        setup_ready = True
                        desk_msg = "Institutional Breakout-Retest Setup Confirmed"

            hold_status = "Price is navigating structural open air."
            in_demand_zone = (cmp <= int_s_top * 1.01) and (cmp >= int_s_bottom * 0.99)
            in_supply_zone = (cmp >= int_r_bottom * 0.99) and (cmp <= int_r_top * 1.01)
            
            if in_demand_zone:
                if cmp > c_open or is_hammer or is_bullish_engulfing:
                    hold_status = f"🟢 LOCAL FLOOR HOLD: Rejection pattern verified inside Internal Demand Zone. Pattern: {candle_pattern}."
                    if trend_bias in ["Bullish", "Retracement"]:
                        setup_ready = True
                        desk_msg = "Local Demand Floor Rebound Setup"
                else:
                    hold_status = f"⏳ Testing Internal Demand Block (₹{round(int_s_bottom, 2)} - {round(int_s_top, 2)}). Watching for confirmation."
            elif in_supply_zone:
                if cmp < c_open or is_shooting_star:
                    hold_status = f"🔴 LOCAL SUPPLY REJECTION CONFIRMED: Heavy distribution wicks left inside local Resistance Block."

            # Integrated Risk Management Desk Cross-Checking Targets against External Boundaries
            sl_coordinate, target_1, target_2 = 0.0, 0.0, 0.0
            if setup_ready:
                sl_coordinate = round(int_s_bottom * 0.998, 2)
                share_risk = cmp - sl_coordinate
                
                if share_risk > 0:
                    target_1 = round(cmp + (share_risk * 1.5), 2)
                    target_2 = round(cmp + (share_risk * 2.5), 2)
                    
                    # FIXED GUARDRAIL: Automatically abort if local targets run straight into the 14-month macro ceiling
                    if target_1 > int_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) collides with Local Resistance Block (₹{round(int_r_bottom, 2)})."
                    elif target_1 > ext_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) runs directly into 14-Month External Macro Ceiling (₹{round(ext_r_bottom, 2)}). Range capped."

            # --- UI PRESENTATION GRID ---
            layout_col1, layout_col2 = st.columns(2)
            
            with layout_col1:
                st.subheader("1. Dual-Layer Market Structure Matrix (Option 3)")
                st.info(mss_msg)
                
                with st.expander("🔍 View Component Layer Breakdown"):
                    st.markdown(f"**🌐 External Macro Bias (12-14 Months):** `{ext_bias}`")
                    st.markdown(f"**⚡ Internal Local Bias (3-4 Months):** `{int_bias}`")
                
                st.subheader("2. Key Internal Structural Zones (3-4 Month Horizon)")
                st.success(f"🟢 **Internal Demand Zone:** ₹{round(int_s_bottom, 2)} - ₹{round(int_s_top, 2)}  \n*(Valid Pivots: {int_s_hits} | Squeeze Counter: {floor_strikes})*")
                st.error(f"🔴 **Internal Supply Zone:** ₹{round(int_r_bottom, 2)} - ₹{round(int_r_top, 2)}  \n*(Valid Pivots: {int_r_hits} | Squeeze Counter: {ceiling_strikes})*")
                
                st.subheader("3. Key External Macro Zones (12-14 Month Horizon)")
                st.markdown(f"**🔷 External Macro Floor:** ₹{round(ext_s_bottom, 2)} - ₹{round(ext_s_top, 2)} *(Historical Touches: {ext_s_hits})*")
                st.markdown(f"**🔶 External Macro Ceiling:** ₹{round(ext_r_bottom, 2)} - ₹{round(ext_r_top, 2)} *(Historical Touches: {ext_r_hits})*")

            with layout_col2:
                st.subheader("4. Breakout & Breakdown Analytics")
                st.write(breakout_status)
                st.caption(f"Intraday Expansion Volume Ratio: {round(v_mult, 2)}x compared to the 20-day baseline average.")
                
                st.subheader("5. Retest Tracker & Structural Rejections")
                st.warning(f"🔄 **Retest Analysis:** {retest_status}")
                st.info(f"⚡ **Zone Price Action:** {hold_status}")
                
                st.subheader("6. Algorithmic Risk Execution Setup")
                if not setup_ready:
                    st.warning(f"⚠️ **Order Desk Status:** {desk_msg}")
                else:
                    st.success(f"✅ **Execution Blueprint Authorized:** {desk_msg}")
                    st.write(f"👉 **Target Entry Vector:** Market Price (₹{cmp})")
                    st.write(f"🛡️ **Institutional Protection SL (0.2% Under Structure):** ₹{sl_coordinate}")
                    st.write(f"🎯 **Target 1 (Minimum 1:1.5 Risk RR Locked):** ₹{target_1} *({round(((target_1-cmp)/cmp)*100,2)}% gain)*")
                    st.write(f"🎯 **Target 2 (Extended 1:2.5 Run Target):** ₹{target_2} *({round(((target_2-cmp)/cmp)*100,2)}% gain)*")

    except Exception as e:
        st.error(f"Operational Parsing Error: {str(e)}")
