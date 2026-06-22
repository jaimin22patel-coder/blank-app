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

# Add/Remove Buttons with Permanent Storage Hooks
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
    """
    Option 3 Engine: Evaluates 12-14 month External Macro structure 
    simultaneously with 3-4 month Internal local structure using daily data.
    """
    highs = df_full['High'].tolist()
    lows = df_full['Low'].tolist()
    
    # Slice arrays to separate data layers
    # Assuming ~21 trading days per month: 4 months ≈ 84 bars, 14 months ≈ 294 bars
    internal_highs = highs[-84:]
    internal_lows = lows[-84:]
    
    # 1. Helper function to capture structural pivot chains
    def extract_pivots(h_arr, l_arr, left_right_strength=3):
        p_highs, p_lows = [], []
        for i in range(left_right_strength, len(h_arr) - left_right_strength):
            if h_arr[i] == max(h_arr[i - left_right_strength : i + left_right_strength + 1]):
                p_highs.append(h_arr[i])
            if l_arr[i] == min(l_arr[i - left_right_strength : i + left_right_strength + 1]):
                p_lows.append(l_arr[i])
        return p_highs, p_lows

    # Extract high-strength pivots for External Macro, lower strength for Internal Local
    ext_highs, ext_lows = extract_pivots(highs, lows, left_right_strength=10)
    int_highs, int_lows = extract_pivots(internal_highs, internal_lows, left_right_strength=3)
    
    # 2. Evaluate External Structure (12-14 Months)
    ext_bias = "Neutral / Consolidation"
    if len(ext_highs) >= 2 and len(ext_lows) >= 2:
        if ext_highs[-1] > ext_highs[-2] and ext_lows[-1] > ext_lows[-2]:
            ext_bias = "📈 Bullish Macro Trend"
        elif ext_highs[-1] < ext_highs[-2] and ext_lows[-1] < ext_lows[-2]:
            ext_bias = "📉 Bearish Macro Trend"
            
    # 3. Evaluate Internal Structure (3-4 Months)
    int_bias = "Neutral"
    if len(int_highs) >= 2 and len(int_lows) >= 2:
        if int_highs[-1] > int_highs[-2] and int_lows[-1] > int_lows[-2]:
            int_bias = "Bullish"
        elif int_highs[-1] < int_highs[-2] and int_lows[-1] < int_lows[-2]:
            int_bias = "Bearish"

    # 4. Formulate Interlocked Tactical Summary
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

# --- DYNAMIC INSTITUTIONAL ZONE ENGINE ---
def extract_pure_order_blocks(df, current_cmp, zone_pct=0.012):
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    opens = df['Open'].values
    
    swing_highs, swing_high_tops = [], []
    swing_lows, swing_low_bottoms = [], []
    
    for i in range(2, len(df) - 2):
        if highs[i] == max(highs[i-2:i+3]):
            swing_highs.append(min(opens[i], closes[i])) 
            swing_high_tops.append(highs[i])             
        if lows[i] == min(lows[i-2:i+3]):
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
        
        # EXTENDED LOOKBACK WINDOW: 14 Months of Daily Data for Option 3 Engine
        df_daily_full = stock.history(period="14mo", interval="1d")    
        df_weekly = stock.history(period="2y", interval="1wk")   
        
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
            
            # Run Option 3 Engine
            mss_msg, trend_bias, ext_bias, int_bias = calculate_dual_layer_mss(df_daily_full)
            
            # Slice down to recent 4 months for proper localized Order Block zone tracking
            df_recent_daily = df_daily_full.iloc[-84:]
            d_s_top, d_s_bottom, d_r_bottom, d_r_top, d_s_hits, d_r_hits = extract_pure_order_blocks(df_recent_daily, cmp)
            w_s_top, w_s_bottom, w_r_bottom, w_r_top, w_s_hits, w_r_hits = extract_pure_order_blocks(df_weekly, cmp, zone_pct=0.02)
            
            # Candlestick Calculations
            c_range = c_high - c_low
            l_wick = min(c_open, cmp) - c_low
            u_wick = c_high - max(c_open, cmp)
            
            is_hammer = c_range > 0 and (l_wick / c_range >= 0.55)
            is_shooting_star = c_range > 0 and (u_wick / c_range >= 0.55)
            
            prev_open = float(df_recent_daily['Open'].iloc[-2])
            prev_close_val = float(df_recent_daily['Close'].iloc[-2])
            is_bullish_engulfing = cmp > c_open and prev_close_val < prev_open and cmp > prev_open and c_open < prev_close_val
            
            candle_pattern = "Standard Candle"
            if is_hammer: candle_pattern = "💎 Institutional Hammer (Liquidity Grab)"
            elif is_shooting_star: candle_pattern = "🛸 Shooting Star (Supply Rejection)"
            elif is_bullish_engulfing: candle_pattern = "🔥 Bullish Engulfing (Institutional Displacement)"

            # Breakout and Strike Counters
            breakout_status = "⚖️ Rangebound: Price is trading inside structural boundaries."
            retest_status = "⏳ No active breakout retest flagged."
            setup_ready = False
            desk_msg = "Awaiting institutional setup conditions..."
            
            recent_highs_list = df_recent_daily['High'].iloc[-20:].tolist()
            recent_lows_list = df_recent_daily['Low'].iloc[-20:].tolist()
            recent_closes_list = df_recent_daily['Close'].iloc[-20:].tolist()
            
            ceiling_strikes = sum(1 for h, c in zip(recent_highs_list, recent_closes_list) if h >= d_r_bottom and c <= d_r_top)
            floor_strikes = sum(1 for l, c in zip(recent_lows_list, recent_closes_list) if l <= d_s_top and c >= d_s_bottom)
            
            historic_closes = df_recent_daily['Close'].iloc[-7:-1].tolist()
            had_daily_breakout = any(hc > d_r_top for hc in historic_closes)
            
            if cmp > d_r_top:
                if v_mult >= 1.4:
                    breakout_status = f"🚀 VERIFIED INSTITUTIONAL BREAKOUT: Confirmed body close above ₹{round(d_r_top, 2)} on heavy volume ({round(v_mult,2)}x)."
                else:
                    breakout_status = f"⚠️ LIQUIDITY TRAP WARNING: Outside close printed at ₹{cmp}, but volume fails institutional threshold ({round(v_mult,2)}x)."
            elif cmp < d_s_bottom:
                if v_mult >= 1.4:
                    breakout_status = f"💥 VERIFIED INSTITUTIONAL BREAKDOWN: Strong structural close below the support floor of ₹{round(d_s_bottom, 2)}."
            
            if had_daily_breakout and (c_low <= d_r_top * 1.01) and (cmp >= d_r_bottom):
                if cmp > c_open or is_hammer:
                    retest_status = f"✅ BREAKOUT RETEST CONFIRMED: Previous Supply Ceiling (₹{round(d_r_bottom, 2)}) successfully flipped and defended as dynamic support."
                    if trend_bias in ["Bullish", "Retracement"]:
                        setup_ready = True
                        desk_msg = "Institutional Breakout-Retest Setup Confirmed"

            hold_status = "Price is navigating structural open air."
            in_demand_zone = (cmp <= d_s_top * 1.01) and (cmp >= d_s_bottom * 0.99)
            in_supply_zone = (cmp >= d_r_bottom * 0.99) and (cmp <= d_r_top * 1.01)
            
            if in_demand_zone:
                if cmp > c_open or is_hammer or is_bullish_engulfing:
                    hold_status = f"🟢 STRUCTURAL FLOOR HOLD: Rejection pattern verified inside Demand Zone. Pattern: {candle_pattern}."
                    # TRADING MODIFICATION: Authorize buys on true local retracements inside dominant macro bull markets
                    if trend_bias in ["Bullish", "Retracement"]:
                        setup_ready = True
                        desk_msg = "Major Demand Floor Rebound Setup"
                else:
                    hold_status = f"⏳ Testing Demand Block (₹{round(d_s_bottom, 2)} - {round(d_s_top, 2)}). Watching for confirmation footprint."
            elif in_supply_zone:
                if cmp < c_open or is_shooting_star:
                    hold_status = f"🔴 SUPPLY REJECTION CONFIRMED: Heavy distribution wicks left inside Resistance Block. Sellers defending."

            # Risk Management Target Desk
            sl_coordinate, target_1, target_2 = 0.0, 0.0, 0.0
            if setup_ready:
                sl_coordinate = round(d_s_bottom * 0.998, 2)
                share_risk = cmp - sl_coordinate
                
                if share_risk > 0:
                    target_1 = round(cmp + (share_risk * 1.5), 2)
                    target_2 = round(cmp + (share_risk * 2.5), 2)
                    
                    if target_1 > d_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) collides with Daily Resistance Wall (₹{round(d_r_bottom, 2)}). Risk-Reward window restricted."
                    elif target_1 > w_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) runs directly into 2-Year Weekly Macro Ceiling (₹{round(w_r_bottom, 2)}). Range capped."

            # --- UI PRESENTATION GRID ---
            layout_col1, layout_col2 = st.columns(2)
            
            with layout_col1:
                st.subheader("1. Dual-Layer Market Structure Matrix (Option 3)")
                st.info(mss_msg)
                
                with st.expander("🔍 View Component Layer Breakdown"):
                    st.markdown(f"**🌐 External Macro Bias (12-14 Months):** `{ext_bias}`")
                    st.markdown(f"**⚡ Internal Local Bias (3-4 Months):** `{int_bias}`")
                    st.caption("Strategic Logic: If Macro is Bullish while Local is Bearish, the tool flags a high-probability 'BULLISH RETRACEMENT' setup profile to catch the dip.")
                
                st.subheader("2. Key Daily Structural Zones (3-4 Month Profile)")
                st.success(f"🟢 **Institutional Demand Zone:** ₹{round(d_s_bottom, 2)} - ₹{round(d_s_top, 2)}  \n*(Valid Touches: {d_s_hits} | Current Squeeze Contact Count: {floor_strikes})*")
                st.error(f"🔴 **Institutional Supply Zone:** ₹{round(d_r_bottom, 2)} - ₹{round(d_r_top, 2)}  \n*(Valid Touches: {d_r_hits} | Current Squeeze Contact Count: {ceiling_strikes})*")
                
                st.subheader("3. Key Weekly Macro Zones (1-2 Year Frame)")
                st.markdown(f"**🔷 Weekly Macro Floor:** ₹{round(w_s_bottom, 2)} - ₹{round(w_s_top, 2)} *(Historical Weight: {w_s_hits} hits)*")
                st.markdown(f"**🔶 Weekly Macro Ceiling:** ₹{round(w_r_bottom, 2)} - ₹{round(w_r_top, 2)} *(Historical Weight: {w_r_hits} hits)*")

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
