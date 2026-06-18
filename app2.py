import streamlit as st
import datetime
import yfinance as yf
import pandas as pd
import pandas_ta as ta

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
        
        df = stock.history(period="1y", interval="1d")
        df_weekly = stock.history(period="2y", interval="1wk")
        
        if not df.empty and len(df) > 50:
            latest_close = round(float(df['Close'].iloc[-1]), 2)
            prev_close = round(float(df['Close'].iloc[-2]), 2)
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            volume_latest = int(df['Volume'].iloc[-1])
            volume_avg = int(df['Volume'].rolling(window=20).mean().iloc[-1])
            
            # Sidebar Metrics Render
            st.sidebar.subheader(f"🇮🇳 Live Feed: {ticker}")
            st.sidebar.metric(label="Current CMP", value=f"₹{latest_close:,}", delta=f"{pct_change}%")
            st.sidebar.write(f"**Today's Volume:** {volume_latest:,}")
            st.sidebar.write(f"**20-Day Avg Volume:** {volume_avg:,}")
            
            # --- CALCULATIONS ---
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df_weekly['EMA_50'] = ta.ema(df_weekly['Close'], length=50)
            
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

            # Pivot Calculation Engine (21-day centered window)
            df['Support'] = df['Low'][(df['Low'] == df['Low'].rolling(window=21, center=True).min())]
            df['Resistance'] = df['High'][(df['High'] == df['High'].rolling(window=21, center=True).max())]
            
            supports = df['Support'].dropna().tolist()
            resistances = df['Resistance'].dropna().tolist()
            
            immediate_sup = max([s for s in supports if s < latest_close], default=latest_close * 0.95)
            major_sup = max([s for s in supports if s < immediate_sup], default=immediate_sup * 0.95)
            
            immediate_res = min([r for r in resistances if r > latest_close], default=latest_close * 1.05)
            major_res = min([r for r in resistances if r > immediate_res], default=immediate_res * 1.05)

            # --- NEW FEATURE: MARKET STRUCTURE SHIFT (MSS) LOGIC ---
            mss_status = "No active trend shift detected. Market maintaining established structure."
            if len(resistances) >= 2:
                last_lower_high = resistances[-1]
                if daily_trend == "Range-bound" and weekly_trend == "Downtrend" and latest_close > last_lower_high:
                    mss_status = f"🚨 MARKET STRUCTURE SHIFT (MSS): Price has broken above the last structural lower high (₹{round(last_lower_high, 2)}). Reversal change of character is underway!"
                elif daily_trend == "Uptrend" and latest_close > immediate_res:
                    mss_status = "🔄 CONTINUATION: Bullish break of structure (BOS) confirmed. Institutions are adding positions."

            # Candlestick Formations Mapping
            candles_found = []
            body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
            total_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
            lower_wick = min(df['Open'].iloc[-1], df['Close'].iloc[-1]) - df['Low'].iloc[-1]
            upper_wick = df['High'].iloc[-1] - max(df['Open'].iloc[-1], df['Close'].iloc[-1])
            
            is_hammer = False
            is_shooting_star = False
            
            if total_range > 0:
                if lower_wick / total_range > 0.6:
                    candles_found.append("Bullish Rejection (Hammer)")
                    is_hammer = True
                if upper_wick / total_range > 0.6:
                    candles_found.append("Bearish Rejection (Shooting Star)")
                    is_shooting_star = True
                if body / total_range > 0.8:
                    candles_found.append("Marubozu Momentum")
            
            if not candles_found:
                candles_found.append("Standard Consolidation Candle")

            # Structural S/R Setup Engine
            sr_confirmation_status = "No structural testing event found at immediate key levels."
            near_support = latest_close <= (immediate_sup * 1.02)
            if near_support and (is_hammer or df['Close'].iloc[-1] > df['Open'].iloc[-1]):
                sr_confirmation_status = f"✅ DEMAND HOLD: Price is stabilizing and holding immediate support at ₹{round(immediate_sup, 2)}. Institutional buyers are defending this level."
            
            near_resistance = latest_close >= (immediate_res * 0.98)
            if near_resistance and (is_shooting_star or df['Close'].iloc[-1] < df['Open'].iloc[-1]):
                sr_confirmation_status = f"⚠️ SUPPLY REJECTION: Price tried to rally but got rejected from immediate resistance at ₹{round(immediate_res, 2)}. Institutional supply blocks are active here."

            # Stage 8 Filter: Risk-to-Reward Validation
            raw_setup_type = "No Setup Available"
            entry, sl, t1, t2, rr_display, action, bias = latest_close, 0.0, 0.0, 0.0, "N/A", "Wait / Sit on Hands", "Neutral"
            confidence = 5

            if daily_trend == "Uptrend":
                test_entry = latest_close
                test_sl = round(immediate_sup * 0.99, 2)
                test_t1 = round(immediate_res, 2)
                
                risk = abs(test_entry - test_sl)
                reward = abs(test_t1 - test_entry)
                ratio = reward / risk if risk > 0 else 0
                
                if ratio >= 1.5:
                    raw_setup_type = "Bullish Long Setup"
                    entry, sl, t1, t2 = test_entry, test_sl, test_t1, round(major_res, 2)
                    rr_display = f"1 : {round(ratio, 2)}"
                    bias = "Bullish"
                    action = "Buy"
                    confidence = 8 if daily_trend == weekly_trend else 6
                    
            elif daily_trend == "Downtrend":
                test_entry = latest_close
                test_sl = round(immediate_res * 1.01, 2)
                test_t1 = round(immediate_sup, 2)
                
                risk = abs(test_sl - test_entry)
                reward = abs(test_entry - test_t1)
                ratio = reward / risk if risk > 0 else 0
                
                if ratio >= 1.5:
                    raw_setup_type = "Bearish Short Setup"
                    entry, sl, t1, t2 = test_entry, test_sl, test_t1, round(major_sup, 2)
                    rr_display = f"1 : {round(ratio, 2)}"
                    bias = "Bearish"
                    action = "Sell / Short"
                    confidence = 8 if daily_trend == weekly_trend else 6

            # Breakout Data Processing
            volume_ratio = volume_latest / volume_avg
            is_breaking_out = latest_close > immediate_res * 0.99 or latest_close < immediate_sup * 1.01
            bo_prob = "High (Genuine)" if (is_breaking_out and volume_ratio > 1.5) else "Low (Trap)" if is_breaking_out else "No structural breakout detected"

            # --- UI RENDERING ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("1. Market Structure")
                st.write(f"**Daily Chart Bias:** `{daily_trend}`")
                st.write(f"**Weekly Chart Bias:** `{weekly_trend}`")
                st.write(f"**Wave Sequence:** {wave_seq}")
                st.info(f"💡 **Structure Shift Log:** {mss_status}")
                
                st.subheader("2. Key Support Levels (21-Day Low Pivot Formula)")
                st.write(f"🔴 **Immediate Support:** ₹{round(immediate_sup, 2)}")
                st.write(f"⭕ **Major Support (Floor):** ₹{round(major_sup, 2)}")
                
                st.subheader("3. Key Resistance Levels (21-Day High Pivot Formula)")
                st.write(f"🟢 **Immediate Resistance:** ₹{round(immediate_res, 2)}")
                st.write(f"🎯 **Major Resistance (Ceiling):** ₹{round(major_res, 2)}")
                
                st.subheader("4. Price Action Interpretation")
                if daily_trend == "Uptrend":
                    st.write("* **Buyer Behavior:** Dominant. Accumulating heavily near support lines.")
                    st.write("* **Seller Behavior:** Passive.")
                else:
                    st.write("* **Buyer Behavior:** Defensive.")
                    st.write("* **Seller Behavior:** Aggressive.")
                st.write(f"* **Active Demand Zone:** ₹{round(immediate_sup, 2)} - ₹{round(immediate_sup * 1.01, 2)}")

                st.subheader("5. Candlestick Analysis")
                st.write(f"**Observed Formations:** {', '.join(candles_found)}")

            with col2:
                st.subheader("6. Breakout / Breakdown Assessment")
                st.write(f"**Probability Score:** `{bo_prob}`")
                st.write(f"**Volume Multiplier:** {round(volume_ratio, 2)}x")
                
                st.subheader("7. Retest Analysis")
                st.write(f"**Status:** {'Retest Completed' if latest_close <= immediate_sup * 1.01 and daily_trend == 'Uptrend' else 'Awaiting Retest'}")
                st.write(f"**Optimal Entry Zone:** ₹{round(immediate_sup, 2)} - ₹{round(immediate_sup * 1.015, 2)}")
                st.write(f"**Invalidity Level:** Close below ₹{round(major_sup, 2)}")
                
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
                
                st.subheader("9. Structural Support & Resistance Confirmation")
                st.info(sr_confirmation_status)
                
                st.subheader("10. Automated Conclusion")
                st.success(f"**Directional Bias:** {bias.upper()} | **Confidence Score:** {confidence}/10")
                st.subheader(f"⚡ Suggested Action: `{action.upper()}`")

    except Exception as e:
        st.error(f"Execution Error: {str(e)}")