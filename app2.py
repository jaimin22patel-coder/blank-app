import streamlit as st
from PIL import Image
import yfinance as yf
import mplfinance as mpf
import io
import os
import requests
import base64

# Set page configuration
st.set_page_config(
    page_title="Auto-Institutional Price Action Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Free Auto-Institutional Price Action Stock Analyzer")
st.caption("Smart Money analysis powered by Free Groq Vision AI (No Quota Limits).")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🔑 Free Setup")
groq_api_key = st.sidebar.text_input("Enter Groq API Key (If not saved in Secrets)", type="password")

st.sidebar.markdown("""
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `SBIN.NS`.
""")

# Core Prompt Framework
INSTITUTIONAL_PROMPT = """You are an Institutional Price Action Analyst specializing in smart money concepts. 
Analyze the provided stock chart image. Find the primary horizontal price levels where major institutional orders are resting, trapped, or deploying.

You must present your core findings strictly using this exact structural layout:

VERDICT: [Strong Buy / Buy on Retest / Accumulate / Hold / Wait / Reduce Position / Sell on Breakdown / Strong Sell]
BULLISH_SCORE: [Number 0-100]
BEARISH_SCORE: [Number 0-100]

### 🎯 Institutional Key Levels Board
| Price Level / Range | Zone Type | Institutional Action / Reason (One Sentence) |
| --- | --- | --- |

Provide data for: Demand Zone, Supply Zone, Breakout Trigger, Stop Loss, and Take Profit.

### 🧭 Market Context Notes
- Provide 2 short, single-sentence bullet points on overall market structure.
"""

# Helper function to convert PIL Image to base64 for vision models
def encode_image_to_base64(pil_img):
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

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
    final_token = st.secrets.get("GROQ_API_KEY", groq_api_key)
    
    if st.button("Run Smart Money Analysis", type="primary"):
        if not final_token:
            st.error("❌ Please enter your Groq API Key in the sidebar or save it as GROQ_API_KEY in Secrets.")
        elif chart_image is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            with st.spinner(f"Analyzing footprints for {ticker_name} via Groq Free Cloud..."):
                try:
                    base64_image = encode_image_to_base64(chart_image)
                    
                    # Groq Cloud API Endpoint
                    API_URL = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {final_token}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "llama-3.2-11b-vision-instant",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": INSTITUTIONAL_PROMPT},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                ]
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": 1024
                    }
                    
                    response = requests.post(API_URL, headers=headers, json=payload)
                    res_json = response.json()
                    
                    if 'choices' in res_json:
                        raw_text = res_json['choices'][0]['message']['content']
                    elif 'error' in res_json:
                        raise Exception(res_json['error']['message'])
                    else:
                        raise Exception("Unexpected backend API structure response.")
                    
                    # Parsing metrics engine
                    verdict, bullish, bearish, clear_markdown_body = "N/A", "0", "0", ""
                    for line in raw_text.split("\n"):
                        if line.upper().startswith("VERDICT:"): verdict = line.split(":", 1)[1].strip()
                        if line.upper().startswith("BULLISH_SCORE:"): bullish = ''.join(c for c in line if c.isdigit())
                        if line.upper().startswith("BEARISH_SCORE:"): bearish = ''.join(c for c in line if c.isdigit())
                    
                    clear_markdown_body = "\n".join([l for l in raw_text.split("\n") if not l.upper().startswith(("VERDICT:", "BULLISH_", "BEARISH_"))]).strip()
                    
                    # UI Layout Rendering
                    st.success(f"### 🏁 Final Verdict: {verdict}")
                    m_col1, m_col2 = st.columns(2)
                    m_col1.metric("🟢 Bullish Smart Money Bias", f"{bullish}%" if bullish else "N/A")
                    m_col2.metric("🔴 Bearish Smart Money Bias", f"{bearish}%" if bearish else "N/A")
                    st.markdown("---")
                    st.markdown(clear_markdown_body)
                    
                except Exception as e:
                    st.error(f"Error accessing the analysis servers: {str(e)}")
