import streamlit as st
from google import genai
from PIL import Image
import yfinance as yf
import mplfinance as mpf
import io
import os

# Set page configuration
st.set_page_config(
    page_title="Auto-Institutional Price Action Analyzer",
    page_icon="📊",
    layout="wide"
)

# Application Header
st.title("📊 Auto-Institutional Price Action Stock Analyzer")
st.caption("Enter any global or Indian ticker to automatically generate a clean chart and execute Smart Money analysis.")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🔑 Setup & Settings")
api_key = st.sidebar.text_input("Enter Gemini API Key (If not saved in Secrets)", type="password")
model_choice = st.sidebar.selectbox("Choose Model", ["gemini-2.5-flash", "gemini-2.5-pro"])

st.sidebar.markdown("""
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `TATASTEEL.NS`.
""")

# Optimized prompt forcing the AI to strictly output key-value data for extraction
INSTITUTIONAL_PROMPT = """
You are an Institutional Price Action Analyst. Analyze the provided chart exactly as a professional smart money trader would. Do NOT use indicator signals.

Provide your output in this EXACT format so the system can parse it cleanly:

VERDICT: [Strong Buy / Buy on Retest / Accumulate / Hold / Wait / Reduce Position / Sell on Breakdown / Strong Sell]
BULLISH_SCORE: [Number 0-100]
BEARISH_SCORE: [Number 0-100]

---SUMMARY---
[Provide a short, 2-sentence summary here]

---SMART_MONEY---
[Provide 3-4 bullet points analyzing stop-loss clusters, retail traps, and liquidity sweeps here]

---STRUCTURE---
[Provide 2-3 bullet points analyzing structural HH/HL context here]

---TRADE_PLAN---
[Provide Entry Zone, Invalidation SL, and Targets here as bullet points]
"""

# Layout Split: Left for data inputs, Right for AI analysis output
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🔍 Fetch Chart Data")
    ticker_name = st.text_input("Stock Ticker Symbol", placeholder="e.g., RELIANCE.NS").strip().upper()
    time_period = st.selectbox("Select History Lookback", ["3mo", "6mo", "1y", "2y"], index=1)
    time_interval = st.selectbox("Candle Timeframe", ["1d", "1wk"], index=0)

    chart_image = None

    if ticker_name:
        with st.spinner(f"Fetching chart for {ticker_name}..."):
            try:
                stock = yf.Ticker(ticker_name)
                df = stock.history(period=time_period, interval=time_interval)
                
                if df.empty:
                    st.error("⚠️ No data found. Make sure to append `.NS` for NSE stocks (e.g. `SBIN.NS`)")
                else:
                    buf = io.BytesIO()
                    custom_style = mpf.make_mpf_style(
                        base_mpf_style='yahoo', 
                        marketcolors=mpf.make_marketcolors(up='green', down='red', inherit=True)
                    )
                    mpf.plot(
                        df, type='candle', style=custom_style, volume=True, 
                        title=f"\n{ticker_name} Clean Structure Chart ({time_interval})",
                        savefig=dict(fname=buf, dpi=150, bbox_inches='tight'), figscale=1.1
                    )
                    buf.seek(0)
                    chart_image = Image.open(buf)
                    st.image(chart_image, caption=f"System Generated Chart for {ticker_name}", use_container_width=True)
            except Exception as e:
                st.error(f"Failed to fetch market data: {str(e)}")

with col2:
    st.subheader("⚡ Automated Institutional Report")
    final_api_key = st.secrets.get("GEMINI_API_KEY", api_key)
    
    if st.button("Run Smart Money Analysis", type="primary"):
        if not final_api_key:
            st.error("❌ Please configure your Gemini API Key.")
        elif chart_image is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            with st.spinner(f"Analyzing footprints for {ticker_name}..."):
                try:
                    client = genai.Client(api_key=final_api_key)
                    content_payload = [chart_image, f"Ticker: {ticker_name}\n" + INSTITUTIONAL_PROMPT]
                    response = client.models.generate_content(model=model_choice, contents=content_payload)
                    raw_text = response.text
                    
                    # Parsing core metrics out of raw AI text to map cleanly to dashboard elements
                    verdict, bullish, bearish, summary, smart_money, structure, trade_plan = "N/A", "0", "0", "", "", "", ""
                    try:
                        for line in raw_text.split("\n"):
                            if line.startswith("VERDICT:"): verdict = line.replace("VERDICT:", "").strip()
                            if line.startswith("BULLISH_SCORE:"): bullish = line.replace("BULLISH_SCORE:", "").strip()
                            if line.startswith("BEARISH_SCORE:"): bearish = line.replace("BEARISH_SCORE:", "").strip()
                        
                        if "---SUMMARY---" in raw_text: summary = raw_text.split("---SUMMARY---")[1].split("---")[0].strip()
                        if "---SMART_MONEY---" in raw_text: smart_money = raw_text.split("---SMART_MONEY---")[1].split("---")[0].strip()
                        if "---STRUCTURE---" in raw_text: structure = raw_text.split("---STRUCTURE---")[1].split("---")[0].strip()
                        if "---TRADE_PLAN---" in raw_text: trade_plan = raw_text.split("---TRADE_PLAN---")[1].strip()
                    except:
                        summary = raw_text # Fallback if text structural block changes slightly
                    
                    # Display 1: Top-Level Clean KPI Scoreboards
                    st.success(f"### 🏁 Verdict: {verdict}")
                    m_col1, m_col2 = st.columns(2)
                    m_col1.metric("🟢 Institutional Bullish Bias", f"{bullish}%")
                    m_col2.metric("🔴 Institutional Bearish Bias", f"{bearish}%")
                    
                    st.markdown(f"**Quick Take:** {summary}")
                    st.markdown("---")
                    
                    # Display 2: Organized Mobile Toggles
                    t1, t2, t3 = st.tabs(["💧 Smart Money & Liquidity", "📉 Structure State", "📝 Trade Setup Plan"])
                    with t1:
                        st.markdown(smart_money if smart_money else "No data returned.")
                    with t2:
                        st.markdown(structure if structure else "No data returned.")
                    with t3:
                        st.markdown(trade_plan if trade_plan else "No data returned.")
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
