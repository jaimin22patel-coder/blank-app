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

st.title("📊 Auto-Institutional Price Action Stock Analyzer")
st.caption("Smart Money analysis with automated error-handling and local cache optimization.")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🔑 Setup & Settings")
api_key = st.sidebar.text_input("Enter Gemini API Key (If not saved in Secrets)", type="password")
model_choice = st.sidebar.selectbox("Choose Model", ["gemini-2.5-flash", "gemini-2.5-pro"])

st.sidebar.markdown("""
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `SBIN.NS`.
""")

# Core Prompt Framework
INSTITUTIONAL_PROMPT = """
You are an Institutional Price Action Analyst specializing in smart money concepts. 
Analyze the provided chart and extract the primary key horizontal price levels where major institutional orders are resting, trapped, or deploying.

You must present your core findings strictly using this exact structural layout:

VERDICT: [Insert only one: Strong Buy / Buy on Retest / Accumulate / Hold / Wait / Reduce Position / Sell on Breakdown / Strong Sell]
BULLISH_SCORE: [Number 0-100]
BEARISH_SCORE: [Number 0-100]

### 🎯 Institutional Key Levels Board
Create a clean markdown table matching these exact column headers:
| Price Level / Range | Zone Type | Institutional Action / Reason (One Sentence) |

Inside the table, map out Demand/Supply zones, Breakout Triggers, Stop Loss, and Take Profits.

### 🧭 Market Context Notes
- Provide 2-3 short, single-sentence bullet points on overall market structure and orderflow context here.
"""

# CACHED ENGINE: Saves your API quota so repeated clicks don't break your tool
@st.cache_data(show_spinner=False)
def get_cached_analysis(chart_bytes, ticker, model, target_prompt, secret_key):
    try:
        img = Image.open(io.BytesIO(chart_bytes))
        client = genai.Client(api_key=secret_key)
        content_payload = [img, f"Ticker: {ticker}\n" + target_prompt]
        response = client.models.generate_content(model=model, contents=content_payload)
        return response.text
    except Exception as api_err:
        return f"ERROR_OCCURRED: {str(api_err)}"

# Layout Split
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🔍 Fetch Chart Data")
    ticker_name = st.text_input("Stock Ticker Symbol", placeholder="e.g., RELIANCE.NS").strip().upper()
    time_period = st.selectbox("Select History Lookback", ["3mo", "6mo", "1y", "2y"], index=1)
    time_interval = st.selectbox("Candle Timeframe", ["1d", "1wk"], index=0)

    chart_image = None
    chart_bytes_for_cache = None

    if ticker_name:
        with st.spinner(f"Fetching chart for {ticker_name}..."):
            try:
                stock = yf.Ticker(ticker_name)
                df = stock.history(period=time_period, interval=time_interval)
                
                if df.empty:
                    st.error("⚠️ No data found. Make sure to append `.NS` for NSE stocks.")
                else:
                    buf = io.BytesIO()
                    custom_style = mpf.make_mpf_style(
                        base_mpf_style='yahoo', 
                        marketcolors=mpf.make_marketcolors(up='green', down='red', inherit=True)
                    )
                    mpf.plot(df, type='candle', style=custom_style, volume=True, savefig=dict(fname=buf, dpi=150, bbox_inches='tight'), figscale=1.1)
                    buf.seek(0)
                    
                    chart_bytes_for_cache = buf.getvalue()
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
        elif chart_image is None or chart_bytes_for_cache is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            with st.spinner(f"Analyzing footprints for {ticker_name}..."):
                # Call the cached function safely
                raw_text = get_cached_analysis(
                    chart_bytes_for_cache, 
                    ticker_name, 
                    model_choice, 
                    INSTITUTIONAL_PROMPT, 
                    final_api_key
                )
                
                # Check if the function caught a raw API error
                if raw_text.startswith("ERROR_OCCURRED:"):
                    error_msg = raw_text.replace("ERROR_OCCURRED:", "").strip()
                    if "429" in error_msg or "quota" in error_msg.lower():
                        st.error("❌ Quota Exhausted! You've used up your free daily requests. Please switch models in the sidebar or wait for your daily reset.")
                    elif "503" in error_msg:
                        st.error("❌ Google servers are temporarily overloaded. Please try clicking the button again in a few seconds.")
                    else:
                        st.error(f"❌ API Error: {error_msg}")
                else:
                    try:
                        # Parsing logic
                        verdict, bullish, bearish, clear_markdown_body = "N/A", "0", "0", ""
                        for line in raw_text.split("\n"):
                            if line.startswith("VERDICT:"): verdict = line.replace("VERDICT:", "").strip()
                            if line.startswith("BULLISH_SCORE:"): bullish = line.replace("BULLISH_SCORE:", "").strip()
                            if line.startswith("BEARISH_SCORE:"): bearish = line.replace("BEARISH_SCORE:", "").strip()
                        
                        clear_markdown_body = "\n".join([l for l in raw_text.split("\n") if not l.startswith(("VERDICT:", "BULLISH_", "BEARISH_"))]).strip()
                        
                        # UI Rendering
                        st.success(f"### 🏁 Final Verdict: {verdict}")
                        m_col1, m_col2 = st.columns(2)
                        m_col1.metric("🟢 Bullish Smart Money Bias", f"{bullish}%")
                        m_col2.metric("🔴 Bearish Smart Money Bias", f"{bearish}%")
                        st.markdown("---")
                        st.markdown(clear_markdown_body)
                    except Exception as parse_err:
                        # Fallback rendering if the formatting didn't split perfectly
                        st.markdown(raw_text)
