import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Price Action Strategy Desk", page_icon="📈", layout="wide")

st.title("🤖 Pure Price Action & Institutional Structure Desk")
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
        st.rerun()
if col_rem.button("❌ Remove", use_container_width=True):
    if ticker in st.session_state["watchlist"]:
        st.session_state["watchlist"].remove(ticker)
        st.session_state["active_ticker"] = st.session_state["watchlist"][0] if st.session_state["watchlist"] else ""
        st.rerun()

# --- PLAYBOOK DEFINITIONS FOR DISPLAY HELP ---
MSS_HELP = {
    "📈 Bullish Structure (Higher Highs / Higher Lows)": {
        "meaning": "The market is establishing a sequential chain of higher peaks and protected valleys. Buyers are in total tactical control.",
        "action": "🟢 PRIMED FOR LONG SEALS. Focus entirely on looking for buy entries inside the Daily Support Zone."
    },
    "📉 Bearish Structure (Lower Highs / Lower Lows)": {
        "meaning": "The market is breaking down into a clear distribution trend. Sellers dominate, creating aggressive overhead pressure.",
        "action": "🔴 DO NOT BUY. Long execution protocols are locked down to avoid catching a falling knife profile."
    },
    "🔄 Volatility Expansion Shift (Higher High + Lower Low)": {
        "meaning": "The price is tracking outside bounds in both directions. Aggressive retail stop hunting is underway by market makers.",
        "action": "🟡 ORDER DESK HALTED. Stand aside and wait for clear range parameters to establish."
    },
    "⚖️ Structural Range Compression (Lower High + Higher Low)": {
        "meaning": "The price is coiling into a tighter apex wedge. Volatility is drying up as a major liquidity expansion building.",
        "action": "🔵 RADAR ON. Monitor closely for a high-volume breakout or breakdown confirmation trigger."
    },
    "⚖️ Balanced Structural Consolidation": {
        "meaning": "The price is trapped in a completely flat ping-pong balance zone between long-term supply and demand walls.",
        "action": "⚪ MONITOR THE BOUNDARIES. Wait for price to drift into the major outer limit zones before seeking setups."
    }
}

# --- DYNAMIC INSTITUTIONAL ZONE ENGINE ---
def extract_pure_order_blocks(df, current_cmp, zone_pct=0.012):
    """
    Finds structural pivots and returns dense ranges based on body-to-wick boundaries 
    prioritized strictly by touch volume frequency.
    """
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    opens = df['Open'].values
    
    swing_highs, swing_high_tops = [], []
    swing_lows, swing_low_bottoms = [], []
    
    # 1. Map true fractal pivot anchors
    for i in range(2, len(df) - 2):
        if highs[i] == max(highs[i-2:i+3]):
            swing_highs.append(min(opens[i], closes[i])) # Zone Base
            swing_high_tops.append(highs[i])             # Zone Extremity
        if lows[i] == min(lows[i-2:i+3]):
            swing_lows.append(max(opens[i], closes[i]))  # Zone Ceiling
            swing_low_bottoms.append(lows[i])            # Zone Floor
            
   # 2. Cluster pivots into dense ranges
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
        
        # FIXED: Removed the walrus operator assignment syntax error
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

# --- CANDLE CLOSES MARKET STRUCTURE SHIFT DETECTOR ---
def calculate_body_close_mss(df):
    """
    Evaluates historical daily candle closes against preceding structural pivot highs/lows 
    to track true trend shift transitions objectively.
    """
    highs = df['High'].tolist()
    lows = df['Low'].tolist()
    closes = df['Close'].tolist()
    
    p_highs = [h for i, h in enumerate(highs[2:-2]) if h == max(highs[i:i+5])]
    p_lows = [l for i, l in enumerate(lows[2:-2]) if l == min(lows[i:i+5])]
    
    if len(p_highs) >= 3 and len(p_lows) >= 3:
        is_hh = p_highs[-1] > p_highs[-2]
        is_hl = p_lows[-1] > p_lows[-2]
        is_lh = p_highs[-1] < p_highs[-2]
        is_ll = p_lows[-1] < p_lows[-2]
        
        if is_hh and is_hl:
            return "📈 Bullish Structure (Higher Highs / Higher Lows)", "Bullish"
        elif is_lh and is_ll:
            return "📉 Bearish Structure (Lower Highs / Lower Lows)", "Bearish"
        elif is_hh and is_ll:
            return "🔄 Volatility Expansion Shift (Higher High + Lower Low)", "Neutral"
        elif is_lh and is_hl:
            return "⚖️ Structural Range Compression (Lower High + Higher Low)", "Neutral"
            
    return "⚖️ Balanced Structural Consolidation", "Neutral"

# --- MAIN EXECUTION FRAMEWORK ---
if ticker:
    try:
        yf_symbol = f"{ticker}.NS"
        stock = yf.Ticker(yf_symbol)
        
        # Strictly Bound Lookback Allocations
        df_daily = stock.history(period="4mo", interval="1d")    # Pure 3-4 Month Horizon for Entry Action
        df_weekly = stock.history(period="2y", interval="1wk")   # 1-2 Year Horizon for Macro Barriers
        
        if not df_daily.empty and len(df_daily) > 30:
            cmp = round(float(df_daily['Close'].iloc[-1]), 2)
            p_close = round(float(df_daily['Close'].iloc[-2]), 2)
            change = round(((cmp - p_close) / p_close) * 100, 2)
            
            # Volume profile components
            v_latest = int(df_daily['Volume'].iloc[-1])
            v_avg = int(df_daily['Volume'].rolling(window=20).mean().iloc[-1])
            v_mult = v_latest / v_avg if v_avg > 0 else 1.0
            
            c_open = round(float(df_daily['Open'].iloc[-1]), 2)
            c_high = round(float(df_daily['High'].iloc[-1]), 2)
            c_low = round(float(df_daily['Low'].iloc[-1]), 2)
            
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"🇮🇳 Asset Vector: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{cmp:,}", delta=f"{change}%")
            
            # Execute Calculations
            mss_msg, trend_bias = calculate_body_close_mss(df_daily)
            
            d_s_top, d_s_bottom, d_r_bottom, d_r_top, d_s_hits, d_r_hits = extract_pure_order_blocks(df_daily, cmp)
            w_s_top, w_s_bottom, w_r_bottom, w_r_top, w_s_hits, w_r_hits = extract_pure_order_blocks(df_weekly, cmp, zone_pct=0.02)
            
            # --- CANDLESTICK ANATOMY RADAR ---
            c_range = c_high - c_low
            l_wick = min(c_open, cmp) - c_low
            u_wick = c_high - max(c_open, cmp)
            c_body = abs(cmp - c_open)
            
            is_hammer = c_range > 0 and (l_wick / c_range >= 0.55)
            is_shooting_star = c_range > 0 and (u_wick / c_range >= 0.55)
            
            # Previous candle details for Engulfing detection
            prev_open = float(df_daily['Open'].iloc[-2])
            prev_close_val = float(df_daily['Close'].iloc[-2])
            prev_body = abs(prev_close_val - prev_open)
            
            is_bullish_engulfing = cmp > c_open and prev_close_val < prev_open and cmp > prev_open and c_open < prev_close_val
            
            # Match current candlestick signature
            candle_pattern = "Standard Candle"
            if is_hammer: candle_pattern = "💎 Institutional Hammer (Liquidity Grab)"
            elif is_shooting_star: candle_pattern = "🛸 Shooting Star (Supply Rejection)"
            elif is_bullish_engulfing: candle_pattern = "🔥 Bullish Engulfing (Institutional Displacement)"

            # --- BREAKOUT, RETEST & ATTEMPT COUNT TRACKING ENGINE ---
            breakout_status = "⚖️ Rangebound: Price is trading inside structural boundaries."
            retest_status = "⏳ No active breakout retest flagged."
            setup_ready = False
            desk_msg = "Awaiting institutional setup conditions..."
            
            # Calculate Strike Counts (Wicks hitting zones without body close breakouts)
            recent_highs_list = df_daily['High'].iloc[-20:].tolist()
            recent_lows_list = df_daily['Low'].iloc[-20:].tolist()
            recent_closes_list = df_daily['Close'].iloc[-20:].tolist()
            
            ceiling_strikes = sum(1 for h, c in zip(recent_highs_list, recent_closes_list) if h >= d_r_bottom and c <= d_r_top)
            floor_strikes = sum(1 for l, c in zip(recent_lows_list, recent_closes_list) if l <= d_s_top and c >= d_s_bottom)
            
            # Historic Breakout Lookback Scanner (Trailing 6 Sessions)
            historic_closes = df_daily['Close'].iloc[-7:-1].tolist()
            had_daily_breakout = any(hc > d_r_top for hc in historic_closes)
            
            if cmp > d_r_top:
                if v_mult >= 1.4:
                    breakout_status = f"🚀 VERIFIED INSTITUTIONAL BREAKOUT: Confirmed body close above ₹{d_r_top} on heavy expansion volume ({round(v_mult,2)}x)."
                else:
                    breakout_status = f"⚠️ LIQUIDITY TRAP WARNING: Outside close printed at ₹{cmp}, but volume fails institutional threshold ({round(v_mult,2)}x)."
            elif cmp < d_s_bottom:
                if v_mult >= 1.4:
                    breakout_status = f"💥 VERIFIED INSTITUTIONAL BREAKDOWN: Strong structural close below the support floor of ₹{d_s_bottom}."
            
            # Retest Evaluation Logic
            if had_daily_breakout and (c_low <= d_r_top * 1.01) and (cmp >= d_r_bottom):
                if cmp > c_open or is_hammer:
                    retest_status = f"✅ BREAKOUT RETEST CONFIRMED: Previous Supply Ceiling (₹{d_r_bottom}) successfully flipped and defended as dynamic support."
                    if trend_bias == "Bullish":
                        setup_ready = True
                        desk_msg = "Institutional Breakout-Retest Setup Confirmed"

            # --- ZONE HOLDS AND SUPPLY REJECTIONS ENGINE ---
            hold_status = "Price is navigating structural open air."
            in_demand_zone = (cmp <= d_s_top * 1.01) and (cmp >= d_s_bottom * 0.99)
            in_supply_zone = (cmp >= d_r_bottom * 0.99) and (cmp <= d_r_top * 1.01)
            
            if in_demand_zone:
                if cmp > c_open or is_hammer or is_bullish_engulfing:
                    hold_status = f"🟢 STRUCTURAL FLOOR HOLD: Rejection pattern verified inside Demand Zone. Pattern: {candle_pattern}."
                    if trend_bias == "Bullish" and not setup_ready:
                        setup_ready = True
                        desk_msg = "Major Demand Floor Rebound Setup"
                else:
                    hold_status = f"⏳ Testing Demand Block (₹{d_s_bottom} - {d_s_top}). Watching for confirmation footprint."
            elif in_supply_zone:
                if cmp < c_open or is_shooting_star:
                    hold_status = f"🔴 SUPPLY REJECTION CONFIRMED: Heavy distribution wicks left inside Resistance Block. Sellers defending."

            # --- RISK MANAGEMENT GRID ENGINE (STRICT > 1:1.5 RR & PROTECTION METRICS) ---
            sl_coordinate, target_1, target_2 = 0.0, 0.0, 0.0
            if setup_ready:
                # Place protection stop loss exactly 0.2% below the absolute structural wick floor
                sl_coordinate = round(d_s_bottom * 0.998, 2)
                share_risk = cmp - sl_coordinate
                
                if share_risk > 0:
                    target_1 = round(cmp + (share_risk * 1.5), 2)
                    target_2 = round(cmp + (share_risk * 2.5), 2)
                    
                    # Macro Structural Overhead Filter
                    if target_1 > d_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) collides with Daily Resistance Wall (₹{d_r_bottom}). Risk-Reward window restricted."
                    elif target_1 > w_r_bottom:
                        setup_ready = False
                        desk_msg = f"❌ Trade Aborted: Target 1 (₹{target_1}) runs directly into 2-Year Weekly Macro Ceiling (₹{w_r_bottom}). Range capped."

            # --- UI PRESENTATION GRID ---
            layout_col1, layout_col2 = st.columns(2)
            
            with layout_col1:
                st.subheader("1. Sequential Market Structure Shifts (MSS)")
                st.info(mss_msg)
                
                if mss_msg in MSS_HELP:
                    with st.expander("📖 View Operational Playbook Definition"):
                        st.markdown(f"**Structural Definition:** {MSS_HELP[mss_msg]['meaning']}")
                        st.markdown(f"**Execution Action:** `{MSS_HELP[mss_msg]['action']}`")
                
                st.subheader("2. Key Daily Structural Zones (3-4 Month Profile)")
                # FIXED: Added clean rounding to 2 decimal places for Daily Zones
                st.success(f"🟢 **Institutional Demand Zone:** ₹{round(d_s_bottom, 2)} - ₹{round(d_s_top, 2)}  \n*(Valid Touches: {d_s_hits} | Current Squeeze Contact Count: {floor_strikes})*")
                st.error(f"🔴 **Institutional Supply Zone:** ₹{round(d_r_bottom, 2)} - ₹{round(d_r_top, 2)}  \n*(Valid Touches: {d_r_hits} | Current Squeeze Contact Count: {ceiling_strikes})*")
                
                st.subheader("3. Key Weekly Macro Zones (1-2 Year Frame)")
                # FIXED: Added clean rounding to 2 decimal places for Weekly Zones
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
