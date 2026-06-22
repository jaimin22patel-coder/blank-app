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

# Fallback UI if Secrets are not configured yet
api_key = st.sidebar.text_input("Enter Gemini API Key (If not saved in Secrets)", type="password")

# Use current generation production-ready models
model_choice = st.sidebar.selectbox("Choose Model", ["gemini-2.5-flash", "gemini-2.5-pro"])

st.sidebar.markdown("""
### Indian Market Format:
Add `.NS` for NSE stocks or `.BO` for BSE stocks.
* *Example:* `RELIANCE.NS`, `TATASTEEL.NS`, `NIFTY=F` (Nifty Futures).
""")

# Core Institutional Prompt Framework
INSTITUTIONAL_PROMPT = """
You are an Institutional Price Action Analyst specializing in the Indian stock market.
Analyze the provided chart exactly as a professional trader at a hedge fund, proprietary trading firm, or institutional desk would.

Do NOT use RSI, MACD, Moving Averages, Supertrend, Bollinger Bands, Ichimoku, or any indicator-based signals.
Base the analysis strictly on Price Action, Market Structure, Supply/Demand, and Liquidity.

Provide your output using clean, bold headers, bullet points, and markdown tables where appropriate. Break your analysis down exactly into these sections:

## 🧭 1. Think Like Smart Money
- Where are retail traders likely buying/selling?
- Where are stop losses clustered & where is liquidity resting?
- Did price sweep liquidity before moving?
- Is the move likely accumulation, distribution, markup, or markdown?
- Is the current move sponsored by institutions or driven by retail emotion?

## 📉 2. Market Structure Analysis
- **HH/HL/LH/LL Status:**
- **Classification:** (Strong Uptrend / Uptrend / Range / Downtrend / Strong Downtrend)
- **Structure State:** (Intact / Weakening / Broken)

## 🎯 3. Institutional Supply & Demand Zones
Create a table listing: Zone Type (Demand/Supply), Status (Fresh/Tested), Strength (Strong/Moderate/Weak), and why institutions may defend it.

## 💧 4. Liquidity & Breakout Quality Analysis
- **Liquidity Targets:** Where is smart money heading next?
- **Breakout/Retest Classification:** (Institutional Breakout / Retail Breakout / False Breakout / Liquidity Grab)
- Was there strong displacement and follow-through? What is the Candle Story?

## 📊 5. Institutional Bias Score
- **Bullish Score:** [0-100]
- **Bearish Score:** [0-100]
*(Base this on Structure, Liquidity, Supply/Demand, and Breakout Quality)*

## 📝 6. Trade Plan (If setup exists)
- **Entry Zone:** (Where institutions are likely accumulating/distributing)
- **Invalidation Level (Stop Loss):**
- **Targets:** Target 1 & Target 2
- **Risk to Reward Ratio:**

## 🏁 7. Final Verdict
**[INSERT ONE: Strong Buy / Buy on Retest / Accumulate / Hold / Wait / Reduce Position / Sell on Breakdown / Strong Sell]**
*Provide a 2-3 sentence explanation of the reasoning in simple language.*
"""

# Layout Split: Left for data inputs, Right for AI analysis output
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("🔍 Fetch Chart Data")
    ticker_name = st.text_input("Stock Ticker Symbol", placeholder="e.g., RELIANCE.NS").strip().upper()
    
    # Structure setup selectors
    time_period = st.selectbox("Select History Lookback", ["3mo", "6mo", "1y", "2y"], index=1)
    time_interval = st.selectbox("Candle Timeframe", ["1d", "1wk"], index=0)

    # Empty canvas initialization for chart memory stream
    chart_image = None

    if ticker_name:
        with st.spinner(f"Fetching chart for {ticker_name}..."):
            try:
                # 1. Download market engine data
                stock = yf.Ticker(ticker_name)
                df = stock.history(period=time_period, interval=time_interval)
                
                if df.empty:
                    st.error("⚠️ No data found. Make sure to append `.NS` for NSE stocks (e.g. `SBIN.NS`)")
                else:
                    # 2. Plot clean chart inside memory buffer using a safe, universal visual style ('yahoo')
                    buf = io.BytesIO()
                    
                    custom_style = mpf.make_mpf_style(
                        base_mpf_style='yahoo', 
                        marketcolors=mpf.make_marketcolors(up='green', down='red', inherit=True)
                    )
                    
                    mpf.plot(
                        df, 
                        type='candle', 
                        style=custom_style, 
                        volume=True, 
                        title=f"\n{ticker_name} Clean Structure Chart ({time_interval})",
                        savefig=dict(fname=buf, dpi=150, bbox_inches='tight'),
                        figscale=1.1
                    )
                    buf.seek(0)
                    
                    # 3. Load processed output to page layout view
                    chart_image = Image.open(buf)
                    st.image(chart_image, caption=f"System Generated Chart for {ticker_name}", use_container_width=True)
                    
            except Exception as e:
                st.error(f"Failed to fetch or render market data: {str(e)}")

with col2:
    st.subheader("⚡ Automated Institutional Report")
    
    # Checks Streamlit secrets panel automatically, defaults back to the manual sidebar text box if missing.
    final_api_key = st.secrets.get("GEMINI_API_KEY", api_key)
    
    if st.button("Run Smart Money Analysis", type="primary"):
        if not final_api_key:
            st.error("❌ Please enter your Gemini API Key in the sidebar or save it in Streamlit Secrets.")
        elif chart_image is None:
            st.error("❌ There is no generated stock chart to analyze yet.")
        else:
            with st.spinner(f"Analyzing institutional footprints for {ticker_name}..."):
                try:
                    # Connect via the current generation client standard
                    client = genai.Client(api_key=final_api_key)
                    
                    # Combine image content and system structure parameters
                    content_payload = [
                        chart_image,
                        f"Analyze this auto-generated chart for ticker: {ticker_name}.\n" + INSTITUTIONAL_PROMPT
                    ]
                    
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=content_payload
                    )
                    
                    st.markdown(response.text)
                    st.success("✅ Analysis Complete!")
                    
                except Exception as e:
                    st.error(f"An error
