import streamlit as st
import yfinance as yf
import mplfinance as mpf
import io
import base64
import requests
import json
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="Auto-Institutional Price Action Analyzer",
    page_icon="📊",
    layout="wide"
)

# Application Header
st.title("📊 Auto-Institutional Price Action Stock Analyzer")
st.caption("Enter any global or Indian ticker to automatically generate a clean chart and execute Smart Money analysis via OpenRouter Free Tier.")
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("🔑 Setup & Settings")
openrouter_key = st.sidebar.text_input("Enter OpenRouter API Key", type="password")

st.sidebar.markdown("""
### 💡 Getting a Free Key:
1. Go to [openrouter.ai](https://openrouter.ai/)
2. Create a free account.
3. Go to **Keys**, generate one, and paste it here. No credit card required.
                    
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `SBIN.NS`.
""")

# Strictly engineered prompt forcing a standardized Markdown Table layout
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

Inside the table, make sure to map out:
1. Fresh Demand / Accumulation Zone
2. Fresh Supply / Distribution Zone
3. Buy Trigger / Liquidity Sweep Level
4. Invalidation Level (Stop Loss)
5. Major Liquidity Target (Take Profit)

### 🧭 Market Context Notes
- Provide 2-3 short, single-sentence bullet points on overall market structure and orderflow context here.
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
    
    if st.button("Run Smart Money Analysis", type="primary"):
        if not openrouter_key:
            st.error("❌ Please configure your OpenRouter API Key.")
        elif chart_image is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            with st.spinner(f"Processing footprints via OpenRouter (Gemini Flash Free)..."):
                try:
                    # Step 1: Convert the PIL image to a Base64 String
                    buffered = io.BytesIO()
                    chart_image.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    data_url = f"data:image/png;base64,{img_base64}"
                    
                    # Step 2: Formulate standard OpenRouter request configuration
                    api_url = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json"
                    }
                    
                    # Using the direct Gemini 2.5 Flash Free endpoint
                    payload = {
                        "model": "google/gemini-2.5-flash:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"Ticker: {ticker_name}\n" + INSTITUTIONAL_PROMPT},
                                    {"type": "image_url", "image_url": {"url": data_url}}
                                ]
                            }
                        ]
                    }
                    
                    # Step 3: Trigger API Call
                    response = requests.post(api_url, headers=headers, json=payload)
                    
                    if response.status_code != 200:
                        st.error(f"OpenRouter API Error ({response.status_code}): {response.text}")
                    else:
                        result = response.json()
                        raw_text = result['choices'][0]['message']['content']
                        
                        # Core variables parsing engine
                        verdict, bullish, bearish, clear_markdown_body = "N/A", "0", "0", ""
                        
                        lines = raw_text.split("\n")
                        remaining_lines = []
                        
                        for line in lines:
                            if line.startswith("VERDICT:"): 
                                verdict = line.replace("VERDICT:", "").strip()
                            elif line.startswith("BULLISH_SCORE:"): 
                                bullish = line.replace("BULLISH_SCORE:", "").strip()
                            elif line.startswith("BEARISH_SCORE:"): 
                                bearish = line.replace("BEARISH_SCORE:", "").strip()
                            else:
                                remaining_lines.append(line)
                                
                        clear_markdown_body = "\n".join(remaining_lines).strip()
                        
                        # UI Presentation Layer
                        st.success(f"### 🏁 Final Verdict: {verdict}")
                        
                        m_col1, m_col2 = st.columns(2)
                        m_col1.metric("🟢 Bullish Smart Money Bias", f"{bullish}%")
                        m_col2.metric("🔴 Bearish Smart Money Bias", f"{bearish}%")
                        st.markdown("---")
                        
                        # Injects the structured markdown block output cleanly
                        st.markdown(clear_markdown_body)
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
