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

# Upgraded model list: Prioritizing gemini-2.0-flash for high free daily limits (1500 RPD)
model_choice = st.sidebar.selectbox("Choose Model", ["gemini-2.0-flash", "gemini-2.5-flash"])

st.sidebar.markdown("""
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `SBIN.NS`.
""")

# Strictly engineered prompt forcing a standardized Markdown Table layout
INSTITUTIONAL_PROMPT = """
You are an Institutional Price Action Analyst specializing in smart money concepts. 
Analyze the provided chart along with the calculated core mathematical data to extract primary horizontal price levels where major institutional orders are resting, trapped, or deploying.

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
    market_data_summary = ""

    if ticker_name:
        with st.spinner(f"Fetching chart for {ticker_name}..."):
            try:
                stock = yf.Ticker(ticker_name)
                df = stock.history(period=time_period, interval=time_interval)
                
                if df.empty:
                    st.error("⚠️ No data found. Make sure to append `.NS` for NSE stocks (e.g. `SBIN.NS`)")
                else:
                    # --- MATH ENGINES (PROMPT GROUNDING) ---
                    # Gather cold numerical data natively for free to avoid AI vision hallucination 
                    last_close = df['Close'].iloc[-1]
                    high_period = df['High'].max()
                    low_period = df['Low'].min()
                    sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
                    
                    market_data_summary = f"""
                    Recent Close Price: {last_close:.2f}
                    Period Structural High: {high_period:.2f}
                    Period Structural Low: {low_period:.2f}
                    20-Period Simple Moving Average: {sma_20:.2f} if available else N/A
                    """
                    
                    # --- CHART RENDERING ENGINE ---
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
            with st.spinner(f"Parsing institutional footprints for {ticker_name}..."):
                try:
                    client = genai.Client(api_key=final_api_key)
                    
                    # Merge structured system text instructions with mathematical hard facts
                    full_prompt = f"{INSTITUTIONAL_PROMPT}\n\n[CRITICAL MATHEMATICAL DATA FOR VERIFICATION]:\n{market_data_summary}"
                    content_payload = [chart_image, f"Ticker: {ticker_name}\n" + full_prompt]
                    
                    response = client.models.generate_content(
                        model=model_choice, 
                        contents=content_payload
                    )
                    raw_text = response.text
                    
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
                    
                    # Directly inject the clean, structured levels table and brief notes
                    st.markdown(clear_markdown_body)
                        
                except Exception as e:
                    # Added clear descriptive handling for quota issues
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        st.error("❌ Free Tier Limit Reached. Please switch the selected model option to 'gemini-2.0-flash' in the sidebar or check back later.")
                    else:
                        st.error(f"An error occurred during processing: {str(e)}")
