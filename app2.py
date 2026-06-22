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
st.caption("Enter any global or Indian ticker to automatically generate a clean chart and execute individual data tracking.")
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

# Strictly engineered prompt forcing the new level-first 3rd column table layout
INSTITUTIONAL_PROMPT = """
You are an Institutional Price Action Analyst specializing in smart money concepts. 
Analyze the provided chart and track each of the following 9 concepts individually. 

You must present your core findings strictly using a clean markdown table matching these exact column headers:
| Setup / Concept | Status | Precise Price / Level | Individual Data Points & Reasons Used to Track This |

Inside the table, evaluate these 9 items row-by-row in this exact order:
1. Market structure (Identify if it is Bullish Shift, Bearish Shift, or Ranging based on structural swing points)
2. Breakout (Identify if there is an active/confirmed breakout past key horizontal resistance based on candle body closes and volume)
3. Breakdown (Identify if there is an active/confirmed breakdown below key horizontal support based on candle body closes and volume)
4. Retest (Identify if price has pulled back to a previously broken level and paused/held)
5. Price hold (Identify if price is consolidating tightly or forming inside bars inside a specific demand/supply area)
6. Price rejection (Identify if price left long upper/lower wicks or pin bars to sweep liquidity and snap back)
7. Stop loss (Provide a precise protective stop-loss level located directly beneath the invalidation structure)
8. Entry point near stop loss (Identify an optimal entry level positioned tightly near the protective stop loss to keep risk low)
9. Risk reward is >= 1:1.5 (Calculate and confirm if the potential reward relative to the stop-loss risk meets or exceeds a 1:1.5 ratio)

Do not include any conversational intro, extra text summaries, or generic explanations. Output only the markdown table.
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
    st.subheader("📊 Individual Price Action Data Tracker")
    final_api_key = st.secrets.get("GEMINI_API_KEY", api_key)
    
    if st.button("Track Individual Setup Data", type="primary"):
        if not final_api_key:
            st.error("❌ Please configure your Gemini API Key.")
        elif chart_image is None:
            st.error("❌ No generated stock chart to analyze.")
        else:
            with st.spinner(f"Tracking separate price action footprints for {ticker_name}..."):
                try:
                    client = genai.Client(api_key=final_api_key)
                    content_payload = [chart_image, f"Ticker: {ticker_name}\n" + INSTITUTIONAL_PROMPT]
                    response = client.models.generate_content(model=model_choice, contents=content_payload)
                    
                    # Directly display the strict layout table response on the dashboard
                    st.markdown(response.text)
                    st.success("✅ Tracking Data Updated!")
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
