import streamlit as st
import datetime
import yfinance as yf
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Automated Price Action Analyzer", page_icon="📈", layout="wide")

st.title("🤖 Advanced Institutional Price Action Analyzer")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("NSE Stock Selection")
raw_ticker = st.sidebar.text_input("NSE Stock Symbol (e.g., SBIN, RELIANCE, SUNPHARMA)", value="SUNPHARMA")
ticker = raw_ticker.upper().strip().replace(".NS", "")

if ticker:
    try:
        yf_symbol = f"{ticker}.NS"
        stock = yf.Ticker(yf_symbol)
        
        # Fetch Daily and Weekly Data structures
        df = stock.history(period="1y", interval="1d")
        df_weekly = stock.history(period="2y", interval="1wk")
        
        if not df.empty and len(df) > 50:
            latest_close = round(float(df['Close'].iloc[-1]), 2)
            prev_close = round(float(df['Close'].iloc[-2]), 2)
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            volume_latest = int(df['Volume'].iloc[-1])
            volume_avg = int(df['Volume'].rolling(window=20).mean().iloc[-1])
            
            # Current Day Candle Metrics for range calculations
            current_high = round(float(df['High'].iloc[-1]), 2)
            current_low = round(float(df['Low'].iloc[-1]), 2)
            current_open = round(float(df['Open'].iloc[-1]), 2)
            
            # Sidebar Metrics Render
            st.sidebar.subheader(f"🇮🇳 Live Feed: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{latest_close:,}", delta=f"{pct_change}%")
            st.sidebar.write(f"**Today's Volume:** {volume_latest:,}")
            st.sidebar.write(f"**20-Day Avg Volume:** {volume_avg:,}")
            
            # --- TREND LOGIC VIA NATIVE EMA ---
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

            # --- MULTI-TIMEFRAME PIVOT ENGINE ---
            # 1. Daily Pivots
            df['Daily_Sup'] = df['Low'][(df['Low'] == df['Low'].rolling(window=21, center=True).min())]
            df['Daily_Res'] = df['High'][(df['High'] == df['High'].rolling(window=21, center=True).max())]
            daily_sups = df['Daily_Sup'].dropna().tolist()
            daily_ress = df['Daily_Res'].dropna().tolist()
            
            d_immediate_sup = max([s for s in daily_sups if s < latest_close], default=latest_close * 0.95)
            d_major_sup = max([s for s in daily_sups if s < d_immediate_sup], default=d_immediate_sup * 0.95)
            d_immediate_res = min([r for r in daily_ress if r > latest_close], default=latest_close * 1.05)
            d_major_res = min([r for r in daily_ress if r > d_immediate_res], default=d_immediate_res * 1.05)

            # 2. Weekly Pivots
            df_weekly['Wk_Sup'] = df_weekly['Low'][(df_weekly['Low'] == df_weekly['Low'].rolling(window=11, center=True).min())]
            df_weekly['Wk_Res'] = df_weekly['High'][(df_weekly['High'] == df_weekly['High'].rolling(window=11, center=True).max())]
            weekly_sups = df_weekly['Wk_Sup'].dropna().tolist()
            weekly_ress = df_weekly['Wk_Res'].dropna().tolist()
            
            w_immediate_sup = max([s for s in weekly_sups if s < latest_close], default=latest_close * 0.93)
            w_immediate_res = min([r for r in weekly_ress if r > latest_close], default=latest_close * 1.07)

            # --- MARKET STRUCTURE SHIFT (MSS) ---
            mss_status = "No active trend shift detected. Market maintaining established structure."
            if len(daily_ress) >= 2:
                last_lower_high = daily_ress[-1]
                if daily_trend == "Range-bound" and weekly_trend == "Downtrend" and latest_close > last_lower_high:
                    mss_status = f"🚨 MARKET STRUCTURE SHIFT (MSS): Price has broken above the last structural lower high (₹{round(last_lower_high, 2)}). Reversal change of character is underway!"
                elif daily_trend == "Uptrend" and latest_close > d_immediate_res:
                    mss_status = "🔄 CONTINUATION: Bullish break of structure (BOS) confirmed. Institutions are adding positions."

            # Candlestick Calculations
            body = abs(latest_close - current_open)
            total_range = current_high - current_low
            lower_wick = min(current_open, latest_close) - current_low
            upper_wick = current_high - max(current_open, latest_close)
            
            is_hammer = total_range > 0 and (lower_wick / total_range > 0.6)
            is_shooting_star = total_range > 0 and (upper_wick / total_range > 0.6)

            # --- PRECISION SECTION 9: REJECTION & HOLDING RANGES ---
            sr_confirmation_status = "No structural testing event found at immediate key levels."
            near_support_zone = latest_close <= (d_immediate_sup * 1.02)
            near_resistance_zone = latest_close >= (d_immediate_res * 0.98)
            
            if near_support_zone and (is_hammer or latest_close > current_open):
                hold_min = current_low
                hold_max = max(current_open, latest_close)
                sr_confirmation_status = f"✅ DEMAND HOLD CONFIRMED: Price is stabilizing and holding immediate support level of ₹{round(d_immediate_sup, 2)}. Active buying range identified between ₹{round(hold_min, 2)} - ₹{round(hold_max, 2)}."
            elif near_resistance_zone and (is_shooting_star or latest_close < current_open):
                reject_min = min(current_open, latest_close)
                reject_max = current_high
                sr_confirmation_status = f"⚠️ SUPPLY REJECTION CONFIRMED: Price faced institutional rejection near resistance level of ₹{round(d_immediate_res, 2)}. Active supply/selling overhead range identified between ₹{round(reject_min, 2)} - ₹{round(reject_max, 2)}."

            # --- PRECISION SECTION 8: RISK FILTER ---
            raw_setup_type = "No Setup Available"
            entry, sl, t1, t2, rr_display, action, bias = latest_close, 0.0, 0.0, 0.0, "N/A", "Wait / Sit on Hands", "Neutral"
            confidence = 5

            if daily_trend == "Uptrend":
                test_entry = latest_close
                test_sl = round(d_immediate_sup * 0.99, 2)
                test_t1 = round(d_immediate_res, 2)
                risk = abs(test_entry - test_sl)
                reward = abs(test_t1 - test_entry)
                ratio = reward / risk if risk > 0 else 0
                
                if ratio >= 1.5:
                    raw_setup_type = "Bullish Long Setup"
                    entry, sl, t1, t2 = test_entry, test_sl, test_t1, round(d_major_res, 2)
                    rr_display = f"1 : {round(ratio, 2)}"
                    bias = "Bullish"
                    action = "Buy"
                    confidence = 8 if daily_trend == weekly_trend else 6
                    
            elif daily_trend == "Downtrend":
                test_entry = latest_close
                test_sl = round(d_immediate_res * 1.01, 2)
                test_t1 = round(d_immediate_sup, 2)
                risk = abs(test_sl - test_entry)
                reward = abs(test_entry - test_t1)
                ratio = reward / risk if risk > 0 else 0
                
                if ratio >= 1.5:
                    raw_setup_type = "Bearish Short Setup"
                    entry, sl, t1, t2 = test_entry, test_sl, test_t1, round(d_major_sup, 2)
                    rr_display = f"1 : {round(ratio, 2)}"
                    bias = "Bearish"
                    action = "Sell / Short"
                    confidence = 8 if daily_trend == weekly_trend else 6

            # --- PRECISION SECTION 6: BREAKOUT VALUES ---
            volume_ratio = volume_latest / volume_avg
            is_breaking_high = latest_close > (d_immediate_res * 0.99)
            is_breaking_low = latest_close < (d_immediate_sup * 1.01)
            
            if is_breaking_high:
                bo_prob = "High (Genuine)" if volume_ratio > 1.5 else "Low (Potential Trap)"
                bo_val_range = f"🚀 BREAKOUT ALIVE: Sustained price action above resistance floor. Active breakout entry execution value range: ₹{round(d_immediate_res, 2)} to ₹{round(d_make_high := d_immediate_res * 1.015, 2)}."
            elif is_breaking_low:
                bo_prob = "High (Genuine)" if volume_ratio > 1.5 else "Low (Potential Trap)"
                bo_val_range = f"💥 BREAKDOWN ALIVE: Sustained price action below support floor. Active breakdown short execution value range: ₹{round(d_immediate_sup * 0.985, 2)} to ₹{round(d_immediate_sup, 2)}."
            else:
                bo_prob = "No Breakout"
                bo_val_range = f"⚖️ CONSOLIDATION: Price trading inside structural boundaries. Breakout triggers only if daily candle closes above ₹{round(d_immediate_res, 2)} or below ₹{round(d_immediate_sup, 2)}."

            # --- UI RENDERING ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Market Structure")
                st.write(f"**Daily Chart Bias:** `{daily_trend}`")
                st.write(f"**Weekly Chart Bias:** `{weekly_trend}`")
                st.write(f"**Wave Sequence:** {wave_seq}")
                st.info(f"💡 **Structure Shift Log:** {mss_status}")
                
                # UPDATED SECTION 2: Multi-Timeframe Supports
                st.subheader("2. Key Support Levels")
                st.write(f"📅 **Daily Immediate Support:** ₹{round(d_immediate_sup, 2)}")
                st.write(f"📅 **Daily Major Floor:** ₹{round(d_major_sup, 2)}")
                st.write(f"🗓️ **Weekly Macro Support:** ₹{round(w_immediate_sup, 2)}")
                
                # UPDATED SECTION 3: Multi-Timeframe Resistances
                st.subheader("3. Key Resistance Levels")
                st.write(f"**Daily Immediate Resistance:** ₹{round(d_immediate_res, 2)}")
                st.write(f"📅 **Daily Major Ceiling:** ₹{round(d_major_res, 2)}")
                st.write(f"🗓️ **Weekly Macro Resistance:** ₹{round(w_immediate_res, 2)}")
                
                # UPDATED SECTION 4: High Precision Interpretation
                st.subheader("4. Price Action Interpretation")
                demand_range_low = round(d_immediate_sup, 2)
                demand_range_high = round(d_immediate_sup * 1.015, 2)
                supply_range_low = round(d_immediate_res * 0.985, 2)
                supply_range_high = round(d_immediate_res, 2)
                
                st.write(f"🟢 **Precision Order Block / Demand Zone:** ₹{demand_range_low} - ₹{demand_range_high}")
                st.write(f"🔴 **Precision Liquidity Pool / Supply Zone:** ₹{supply_range_low} - ₹{supply_range_high}")
                st.write(f"📈 **Volume Pulse:** Trading at `{round(volume_ratio, 2)}x` average institutional volume.")

                st.subheader("5. Candlestick Analysis")
                candles_found = []
                if is_hammer: candles_found.append("Bullish Rejection (Hammer)")
                if is_shooting_star: candles_found.append("Bearish Rejection (Shooting Star)")
                if body / (total_range if total_range > 0 else 1) > 0.8: candles_found.append("Marubozu Momentum")
                if not candles_found: candles_found.append("Standard Consolidation Candle")
                st.write(f"**Observed Formations:** {', '.join(candles_found)}")

            with col2:
                # UPDATED SECTION 6: Breakout/Breakdown Target Ranges
                st.subheader("6. Breakout / Breakdown Assessment")
                st.write(f"**Probability Score:** `{bo_prob}`")
                st.write(f"**Volume Multiplier:** {round(volume_ratio, 2)}x")
                st.warning(bo_val_range)
                
                st.subheader("7. Retest Analysis")
                st.write(f"**Status:** {'Retest Completed' if latest_close <= d_immediate_sup * 1.015 and daily_trend == 'Uptrend' else 'Awaiting Retest'}")
                st.write(f"**Optimal Entry Zone:** ₹{demand_range_low} - ₹{demand_range_high}")
                st.write(f"**Invalidity Level:** Close below ₹{round(d_major_sup, 2)}")
                
                st.subheader("8. Algorithmic Trade Setup (Risk Filtered ≥ 1:1.5)")
                if raw_setup_type == "No Setup Available":
                    st.warning("⚠️ No Trade Setup Generated: The structural distance to target does not meet the minimum required Risk-to-Reward ratio of 1:1.5.")
                else:
                    st.info(f"**Structure Found:** {raw_setup_type}")
                    st.write(f"👉 **Entry Price:** ₹{entry}")
                    st.write(f"🛑 **Stop Loss:** ₹{sl}")
                    st.write(f"🎯 **Target 1:** ₹{t1}")
                    st.write(f"🚀 **Target 2:** ₹{t2}")
                    st.metric(label="Calculated Risk-to-Reward Ratio", value=rr_display)
                
                # UPDATED SECTION 9: Structural S/R Rejection/Holding Values
                st.subheader("9. Structural Support & Resistance Confirmation")
                st.info(sr_confirmation_status)
                
                st.subheader("10. Automated Conclusion")
                st.success(f"**Directional Bias:** {bias.upper()} | **Confidence Score:** {confidence}/10")
                st.subheader(f"⚡ Suggested Action: `{action.upper()}`")

    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
