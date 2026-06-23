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
st.caption("Smart Money analysis with automated multi-key rate limit protection.")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🔑 Setup & Settings")
api_key = st.sidebar.text_input("Manual Backup Key (Optional)", type="password")
model_choice = st.sidebar.selectbox("Choose Model", ["gemini-2.5-flash", "gemini-2.5-pro"])

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

# Layout Split
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
                    st.error("⚠️ No data found. Make sure to append `.NS` for NSE stocks.")
                else:
                    buf = io.BytesIO()
                    custom_style = mpf.make_mpf_style(
                        base_mpf_style='yahoo', 
                        marketcolors=mpf.make_marketcolors(up='green', down='red', inherit=True)
                    )
                    mpf.plot(df, type='candle', style=custom_style, volume=True, savefig=dict(fname=buf, dpi=150, bbox_inches='tight'), figscale=1.1)
                    buf.seek(0)
                    chart_image = Image.open(buf)
                    st.image(chart_image, caption=f"System Generated Chart for {ticker_name}", use_container_width=True)
            except Exception as e:
                st.error(f"Failed to fetch market data: {str(e)}")

with col2:
    st.subheader("⚡ Automated Institutional Report")
    
    # Gathering pool of keys from secrets
    api_keys_pool = []
    if "GEMINI_API_KEY_1" in st.secrets: api_keys_pool.append(st.secrets["GEMINI_API_KEY_1"])
    if "GEMINI_API_KEY_2" in st.secrets: api_keys_pool.append(st.secrets["GEMINI_API_KEY_2"])
    if "GEMINI_API_KEY_3" in st.secrets: api_keys_pool.append(st.secrets["GEMINI_API_KEY_3"])
    if "GEMINI_API_KEY" in st.secrets: api_keys_pool.append(st.secrets["GEMINI_API_KEY"])
    if api_key: api_keys_pool.append(api_key) # Append manual sidebar key if entered
    
    if st.button("Run Smart Money Analysis", type="primary"):
        if not api_keys_pool:
            st.error("❌ No API Keys found. Please add keys to Streamlit Secrets.")
        elif chart_image is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            success = False
            # Loop through our keys pool until one works
            for idx, current_key in enumerate(api_keys_pool):
                with st.spinner(f"Attempting analysis using Key Slot {idx + 1}..."):
                    try:
                        client = genai.Client(api_key=current_key)
                        content_payload = [chart_image, f"Ticker: {ticker_name}\n" + INSTITUTIONAL_PROMPT]
                        response = client.models.generate_content(model=model_choice, contents=content_payload)
                        raw_text = response.text
                        
                        # Parsing
                        verdict, bullish, bearish, clear_markdown_body = "N/A", "0", "0", ""
                        for line in raw_text.split("\n"):
                            if line.startswith("VERDICT:"): verdict = line.replace("VERDICT:", "").strip()
                            if line.startswith("BULLISH_SCORE:"): bullish = line.replace("BULLISH_SCORE:", "").strip()
                            if line.startswith("BEARISH_SCORE:"): bearish = line.replace("BEARISH_SCORE:", "").strip()
                        
                        clear_markdown_body = "\n".join([l for l in raw_text.split("\n") if not l.startswith(("VERDICT:", "BULLISH_", "BEARISH_"))]).strip()
                        
                        st.success(f"### 🏁 Final Verdict: {verdict}")
                        m_col1, m_col2 = st.columns(2)
                        m_col1.metric("🟢 Bullish Smart Money Bias", f"{bullish}%")
                        m_col2.metric("🔴 Bearish Smart Money Bias", f"{bearish}%")
                        st.markdown("---")
                        st.markdown(clear_markdown_body)
                        
                        success = True
                        st.success(f"✅ Analysis Complete (Handled by Key Slot {idx + 1})")
                        break # Break out of loop since request succeeded
                        
                    except Exception as e:
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            st.warning(f"⚠️ Key Slot {idx + 1} is exhausted. Trying next slot...")
                            continue # Continue loop to next key index
                        else:
                            st.error(f"An unexpected error occurred: {str(e)}")
                            break
            
            if not success:
                st.error("❌ All available API keys are currently exhausted for today. Please wait or add another backup key.")
